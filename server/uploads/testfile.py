import os
from datetime import datetime

import uvicorn
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends

import jwt

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from models import UserModel
from utils import log

from database import User, FileUpload

JWT_SECRET = 'this-is-very-secret-dont-leak'

app = FastAPI()
pw_hasher = PasswordHasher()


def get_current_user(request: Request) -> str:
    jwt_token = request.cookies.get('Authorization')

    if jwt_token is None:
        raise HTTPException(403, 'You need to login to use this feature.')

    jwt_token = jwt_token.split(' ')[-1]
    username = jwt.decode(jwt_token, key=JWT_SECRET, algorithms=['HS256']).get('username')
    return username


# Cadastro de usuário
@app.post('/register')
def register(user_in: UserModel):
    if User.select().where(User.username == user_in.username).count() > 0:
        log.info(f'Tried to register existing username {user_in.username} (returned 409)')
        raise HTTPException(409, 'Username already exists.')

    # Calculamos o hash a partir da senha e criamos o usuário no banco de dados
    password_hash = pw_hasher.hash(user_in.password.get_secret_value())
    new_user = User.create(username=user_in.username, password_hash=password_hash)
    assert new_user is not None

    log.info(f'Registered user {user_in.username}')
    return user_in.dict(exclude={'password'})

# Fazemos o login e retornamos no corpo e cookies o token JWT a ser usado para autenticação.
@app.post('/login')
def login(response: Response, user_in: UserModel):

    # Pegar usuário do banco de dados
    user_db = User.select().where(User.username == user_in.username).first()

    # Verificar existência de usuário
    if not user_db:
        log.info(f'Tried to login with non-existent user {user_in.username}')
        raise HTTPException(404, 'User not found.')

    # Verificar hash de senha
    try:
        pw_hasher.verify(user_db.password_hash, user_in.password.get_secret_value())
    except VerifyMismatchError:
        log.info(f'Tried to login with wrong password for user {user_in.username}')
        raise HTTPException(403, f'Invalid password for username {user_in.username}')

    # Gerar token JWT de autenticação
    jwt_token = jwt.encode({'username': user_in.username}, key=JWT_SECRET, algorithm='HS256').decode()

    log.info(f'Successfully logged in {user_in.username}')
    response.set_cookie('Authorization', f'Bearer {jwt_token}')
    return {
        'username': user_in.username,
        'jwt_token': jwt_token
    }


# Retornar lista com arquivos já enviados
@app.get('/files')
def get_files(current_user: str = Depends(get_current_user)):

    db_files = []
    for file in FileUpload.select():
        db_files.append({
            'filename': file.filename,
            'uploaded_by': file.uploaded_by.username,
            'uploaded_at': file.uploaded_at
        })
    return db_files

# Rota de upload de arquivo
@app.post("/upload")
async def upload_file(current_user: str = Depends(get_current_user), file: UploadFile = File(...)):

    # Verificamos se o arquivo existe no banco de dados, e não na pasta de upload, pela simplicidade
    if FileUpload.select().where(FileUpload.filename == file.filename).count() > 0:
        log.info(f'Tried to upload existing filename {file.filename} (returned 409)')
        raise HTTPException(409, 'Filename already exists.')

    file_path = os.path.join(os.getcwd(), 'uploads', file.filename)

    # Lemos o corpo da mensagem pra escrita em disco de forma iterativa, a fim de não estourar
    # a memória disponível do servidor em caso de um arquivo grande
    with open(file_path, 'wb') as fd:
        while True:
            chunk = file.file.read(1000)
            fd.write(chunk)
            if chunk == b'':
                break

    # Criamos entrada do arquivo no banco de dados
    FileUpload.create(uploaded_by=current_user, uploaded_at=datetime.now(), filename=file.filename)
    log.info(f'Successfully created uploaded file {file.filename}')

    return {"filename": file.filename}


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
