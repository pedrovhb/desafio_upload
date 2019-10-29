import sys

from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QWidget, QApplication, QStackedLayout, QSystemTrayIcon, QMenu, QAction

import requests

from utils import log

from view_login import LoginWidget
from view_upload import UploadViewWidget


# Widget principal, que cuida do ícone no system tray e contém as telas de upload e login
class MainWidget(QWidget):

    def __init__(self, app):
        QWidget.__init__(self)
        log.info('Creating MainWidget')

        # Configurar janela e sessão requests
        self.setWindowTitle('Desafio Upload')
        self.setWindowIcon(QIcon("icon.png"))
        self.session = requests.Session()

        # Configurar telas mostradas em StackedLayout
        self.stackedLayout = QStackedLayout()

        self.login_layout = LoginWidget(self.session)
        self.login_layout.did_login.connect(self.go_to_main_ui)
        self.setFixedSize(self.login_layout.size())

        self.main_layout = UploadViewWidget(self.session)

        self.stackedLayout.addWidget(self.login_layout)
        self.stackedLayout.addWidget(self.main_layout)

        self.setLayout(self.stackedLayout)

        # Inicializar variáveis relacionadas ao comportamento de system tray
        self.closeEvent = self.on_close
        self.system_tray = QSystemTrayIcon()
        self.system_tray.setContextMenu(QMenu('Hi!', self))

        # Tray menu
        self.tray = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray_menu = QMenu(self)

        action_show_window = QAction("Mostrar janela principal", self)
        action_show_window.triggered.connect(self.on_show_main_window)
        self.tray_menu.addAction(action_show_window)

        action_exit = QAction("Fechar", self)
        action_exit.triggered.connect(app.exit)
        self.tray_menu.addAction(action_exit)

        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.hide()

    # # # # # # # # # # # # # # # # # # # #
    # Transição entre telas

    def go_to_main_ui(self, username: str):
        self.main_layout.label_welcome_username.setText(f'Bem-vindo, {username}.')
        self.stackedLayout.setCurrentIndex(1)

    # # # # # # # # # # # # # # # # # # # #
    # Interação com o system tray e visibilidade da janela principal

    def on_close(self, event):
        log.info('Moving program to tray')
        self.tray.show()

    def on_show_main_window(self):
        log.info('Moving program from tray to window')
        self.show()
        self.tray.hide()

    def on_tray_activated(self, event: QSystemTrayIcon.ActivationReason):
        if event == QSystemTrayIcon.ActivationReason.Trigger:
            self.on_show_main_window()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    widget = MainWidget(app)
    widget.show()

    sys.exit(app.exec_())
