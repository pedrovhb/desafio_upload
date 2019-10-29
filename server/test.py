import os

from starlette.testclient import TestClient
from main import app

client = TestClient(app)

jwt_token = None


def test_register():
    r = client.post('/register', json={
        'username': 'pedrovhb',
        'password': 'abc123'
    })
    assert r.status_code == 200


def test_register_fail_username_exists():
    r = client.post('/register', json={
        'username': 'pedrovhb',
        'password': 'abc123'
    })
    assert r.status_code == 409


def test_register_fail_username_length():
    r = client.post('/register', json={
        'username': 'ab',
        'password': 'abc123'
    })
    assert r.status_code == 422
    r = client.post('/register', json={
        'username': 'loooooooong_user',
        'password': 'abc123'
    })
    assert r.status_code == 422


def test_login_fail():
    r = client.post('/login', json={
        'username': 'pedrovhb',
        'password': 'wrongpwd'
    })
    assert r.status_code == 403
    r = client.post('/login', json={
        'username': 'no-user',
        'password': 'wrongpwd'
    })
    assert r.status_code == 404


def test_unauthorized():
    r = client.get('/files')
    assert r.status_code == 403


def test_login():
    r = client.post('/login', json={
        'username': 'pedrovhb',
        'password': 'abc123'
    })
    assert r.status_code == 200
    assert 'Authorization' in r.cookies


def test_get_empty_files():
    r = client.get('/files')
    assert r.status_code == 200
    assert r.json() == []


def test_upload_file():
    test_file_path = os.path.join(os.getcwd(), 'uploads', 'testfile.py')
    if os.path.exists(test_file_path):
        os.remove(test_file_path)

    with open('main.py', 'rb') as fd:
        files = {"file": ('testfile.py', fd, 'multipart/form-data')}
        r = client.post('/upload', files=files)
    assert r.status_code == 200


def test_upload_existing_file():
    with open('main.py', 'rb') as fd:
        files = {"file": ('testfile.py', fd, 'multipart/form-data')}
        r = client.post('/upload', files=files)
    assert r.status_code == 409


def test_get_files():
    r = client.get('/files')
    assert r.json()[0]['filename'] == 'testfile.py'
    assert r.json()[0]['uploaded_by'] == 'pedrovhb'
    assert r.status_code == 200
