from pydantic import BaseModel, Schema
from pydantic.types import SecretStr


# Modelo de entrada da API (corpo da requisição deve conter campos "username" e "password"
class UserModel(BaseModel):
    username: str = Schema(..., min_length=3, max_length=12)

    # O uso do tipo SecretStr do pydantic faz com que não tenhamos que nos preocupar com um log acidental
    # da senha do usuário; quando printada, ela produz somente "*******". Pra conseguir seu valor real é
    # necessário chamar um método específico do objeto.
    password: SecretStr = ...
