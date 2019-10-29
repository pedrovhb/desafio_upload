import logging
import os
import sys

from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile
from PySide2.QtWidgets import *

server_endpoint = 'http://localhost:8000'


# Carrega arquivo .ui gerado pelo Qt Designer e retorna widget
def load_ui(ui_file: str, parent_widget=None) -> QWidget:
    log.info(f'Loading UI file {ui_file}')
    ui_path = os.path.join(os.getcwd(), 'ui', ui_file)
    file = QFile(ui_path)
    file.open(QFile.ReadOnly)
    loader = QUiLoader()
    return loader.load(file, parent_widget)


# Log é mais facilmente extensível e informativo que print
log = logging.getLogger('desafio_upload_client')
log.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)
