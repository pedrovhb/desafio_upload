import requests

from PySide2.QtWidgets import *
from PySide2.QtCore import Signal, QThread

from utils import load_ui, server_endpoint, log


class LoginWidget(QWidget):
    did_login = Signal(str)
    did_register = Signal(str)

    def __init__(self, session: requests.Session):
        QWidget.__init__(self)
        log.info('Creating LoginWidget')

        self.session = session
        self.login_started = Signal()

        # Carregar UI gerada pelo Qt Designer
        self.login_layout = load_ui('login.ui', self)
        self.setFixedSize(self.login_layout.size())

        # Armazenar referências de widgets usados
        self.login_button: QPushButton = self.login_layout.findChild(QPushButton, 'login_button')
        self.register_button: QPushButton = self.login_layout.findChild(QPushButton, 'register_button')
        self.login_username: QLineEdit = self.login_layout.findChild(QLineEdit, 'login_username')
        self.login_password: QLineEdit = self.login_layout.findChild(QLineEdit, 'login_password')
        self.label_error: QLabel = self.login_layout.findChild(QLabel, 'label_error')

        # Conectar sinais de login
        self.login_button.clicked.connect(self.do_login)
        self.login_username.returnPressed.connect(self.do_login)
        self.login_password.returnPressed.connect(self.do_login)

        # Conectar sinal de cadastro e mensagem de sucesso ao concluir cadastro
        self.register_button.clicked.connect(self.do_register)
        self.did_register.connect(self.show_register_success)

    # # # # # # # # # # # # # # # # # # # #
    # Ativação de thread de login/cadastro

    def do_login(self):
        self.do_login_register('login')

    def do_register(self):
        self.do_login_register('register')

    # Cria a thread de login e desabilita formulário
    def do_login_register(self, operation: str):
        self.set_login_form_enabled(False)
        self.label_error.setText('')

        thread_task = self.DoLoginRegister(self, operation)
        thread_task.signal_login_register_failed.connect(self.login_register_failed)
        thread_task.start()

    # # # # # # # # # # # # # # # # # # # #
    # Resposta a sucesso/falha de login/cadastro

    # Slot; mostra mensagem de erro e habilita formulário de login
    def login_register_failed(self, message: str):
        self.set_login_form_enabled(True)
        self.label_error.setText(message)

    # Mostra mensagem de sucesso ao concluir cadastro
    def show_register_success(self, username: str):
        self.set_login_form_enabled(True)
        msg_box = QMessageBox()
        msg_box.setWindowTitle('Sucesso')
        msg_box.setText(f'Bem-vindo, {username}!\nPor favor, faça login.')
        msg_box.exec()

    # Habilitar/desabilitar formulário de login enquanto a requisição de login está sendo feita
    def set_login_form_enabled(self, enabled):
        self.login_button.setEnabled(enabled)
        self.register_button.setEnabled(enabled)
        self.login_username.setEnabled(enabled)
        self.login_password.setEnabled(enabled)

    # # # # # # # # # # # # # # # # # # # #
    # Thread de login/cadastro

    class DoLoginRegister(QThread):
        signal_login_register_failed = Signal(str)

        def __init__(self, parent: QWidget, operation: str):
            super().__init__(parent)
            self.operation = operation
            assert self.operation in ('login', 'register')
            log.info(f'Creating {self.operation} thread...')

        def run(self):
            log.info(f'Starting {self.operation} thread...')
            parent = self.parent()

            # Iniciamos a requisição de login ou cadastro.
            try:
                r = parent.session.post(f'{server_endpoint}/{self.operation}', json={
                    'username': parent.login_username.text(),
                    'password': parent.login_password.text()
                })
            # ConnectionError não é um erro gerado pelo servidor, mas sim de falha de conexão.
            except requests.exceptions.ConnectionError:
                log.info(f'{self.operation} failed: connection to server failed.')
                self.signal_login_register_failed.emit('Erro ao conectar ao servidor.')
                return

            # Verificamos se a operação de login/cadastro teve sucesso...
            if self.operation == 'login' and r.status_code == 200:
                parent.did_login.emit(r.json()['username'])
                log.info(f'Login successful ({r.json()["username"]})')
            elif self.operation == 'register' and r.status_code == 200:
                parent.did_register.emit(r.json()['username'])
                log.info(f'Registration successful ({r.json()["username"]})')

            # Se não houve sucesso, indicamos ao usuário o erro ocorrido, se possível
            else:
                error_codes = {
                    403: 'Usuário ou senha incorretos.',
                    404: 'Usuário não encontrado.',
                    409: 'Usuário já existente',
                    422: 'Dados inválidos.'
                }
                log.info(f'{self.operation} failed: {r.status_code}\n{r.json()}')
                error_message = error_codes.get(r.status_code, 'Houve um erro.')
                self.signal_login_register_failed.emit(error_message)
