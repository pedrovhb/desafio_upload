# Programa de Upload de Arquivos com Qt - Servidor

O programa aqui contido é o back-end escrito com FastAPI de um sistema bem simples de demostração que faz o cadastro,
login, e recebe uploads dos usuários da aplicação cliente, contida em outro repositório.

# Execução

Obs.: Suponho aqui que `python` chama o Python 3.7+. Se necessário, substitua o comando `python` por `python3` ou 
`python3.7`.

* Crie um ambiente virtual para instalação das bibliotecas necessárias:

``python -m venv venv``

* Ative o ambiente virtual:

``venv\Scripts\activate``

* Instale as bibliotecas requeridas:

``pip install -r requirements.txt``

* Execute o servidor:

``python main.py``

# Tecnologias usadas

## FastAPI

O FastAPI é uma micro-framework parecida com Flask, mas vem com alguns brindes. Um deles é a validação automática 
de modelos de entrada e saída, usando o Pydantic. O Pydantic verifica que todos os campos obrigatórios estão presentes,
que os campos estão dentro das limitações impostas (por exemplo, de tamanho máximo de string pra dados textuais e entre 
um valor mínimo e máximo pra dados numéricos).

Outra vantagem legal é que ele automaticamente gera documentação online, com funcionalidade no estilo "postman" de
envio de requisições e com tipos e estruturas automaticamente anotadas com base nos modelos definidos por Pydantic.
Experimente acessar http://localhost:8000/docs ! 

## Peewee

O Peewee é um ORM Python parecido com o SQLAlchemy, mas um pouco mais simples. Como a maioria dos ORMs, tem a vantagem 
de proporcionar uma interface comum pra vários sistemas de bancos de dados. Aqui foi usado o SQLite, mas poderíamos 
facilmente usar o PostgreSQL com poucas ou nenhuma modificação ao código.

## Argon2

Já escrevi brevemente [no meu blog](https://pedrovhb.com/como-sites-com-login-nao-guardam-sua-senha-e-porque-nao-devem/)
 sobre como não é seguro armazenar senhas em texto simples. O Argon2 é um algoritmo de hash projetado especificamente 
pra senhas e que também automaticamente gera e armazena um salt, o tornando uma boa escolha pra isso.

## JWT

JWT é um mecanismo stateless de autenticação que garante a integridade dos dados através de criptografia simétrica.
Os dados que o cliente carrega (por exemplo, um nome de usuário) podem ser decodados sem a chave privada, mas com 
a garantia de que o servidor os gerou e assinou.

# Testes

Estando o ambiente virtual ativo, os testes podem ser realizados com o seguinte comando:

``pytest test.py``

O arquivo .ini garante que a variável de ambiente TEST_DB está setada durante a execução, ativando assim 
o uso de um banco de dados de teste separado do principal, e que é limpo a cada execução dos testes.

Os testes têm 99% de cobertura geral, o 1% sendo a linha de execução do servidor sob `if __name__ == '__main__'`.