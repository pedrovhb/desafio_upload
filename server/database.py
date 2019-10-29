import os

import peewee

from utils import log

db = peewee.SqliteDatabase(os.path.join(os.getcwd(), 'uploads.db'))

# Se estivermos executando um teste, usamos um arquivo novo de banco de dados
if 'TEST_DB' in os.environ:
    log.info('Using test database.')

    # Limpar banco de dados de testes, se existir
    if os.path.exists(os.path.join(os.getcwd(), 'test_uploads.db')):
        os.remove(os.path.join(os.getcwd(), 'test_uploads.db'))

    db = peewee.SqliteDatabase('test_uploads.db')


class User(peewee.Model):
    username = peewee.CharField(primary_key=True)
    password_hash = peewee.CharField()

    class Meta:
        database = db


class FileUpload(peewee.Model):
    filename = peewee.CharField(primary_key=True)
    uploaded_by = peewee.ForeignKeyField(User, backref='uploads')
    uploaded_at = peewee.DateTimeField()

    class Meta:
        database = db


db.create_tables([User, FileUpload])
