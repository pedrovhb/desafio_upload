import os
from datetime import datetime
from typing import List

import requests
from requests_toolbelt import MultipartEncoderMonitor

from PySide2.QtWidgets import *
from PySide2.QtGui import QDragEnterEvent, QDropEvent
from PySide2.QtCore import Signal, QStringListModel, QThread, QTimer

from utils import load_ui, server_endpoint, log


class UploadViewWidget(QWidget):

    def __init__(self, session: requests.Session):
        QWidget.__init__(self)
        log.info('Creating UploadViewWidget')

        # Usamos a mesma sessão previamente autenticada (já tem token JWT no cookie Authorization)
        self.session = session

        self.selected_file = None

        # Carregar interface gerada pelo Qt Designer
        self.upload_layout = load_ui('upload.ui', self)
        self.setFixedSize(self.upload_layout.size())

        # Pegar referências de widgets
        self.button_select_file: QPushButton = self.upload_layout.findChild(QPushButton, 'button_select_file')
        self.button_upload: QPushButton = self.upload_layout.findChild(QPushButton, 'button_upload')
        self.label_drop_file: QLabel = self.upload_layout.findChild(QLabel, 'label_drop_file')
        self.progress_bar_upload: QProgressBar = self.upload_layout.findChild(QProgressBar, 'progress_bar_upload')
        self.list_past_uploads: QListView = self.upload_layout.findChild(QListView, 'list_past_uploads')
        self.label_welcome_username: QLabel = self.upload_layout.findChild(QLabel, 'label_welcome_username')

        # Habilitar seleção de arquivo por drag-and-drop
        self.label_drop_file.dragEnterEvent = self.dragEnterEvent
        self.setAcceptDrops(True)

        # Conectar eventos de botão e login
        self.button_select_file.clicked.connect(self.pick_file)
        self.button_upload.clicked.connect(self.button_upload_clicked)

        # Agendar atualização contínua de lista de arquivos já enviados
        self.uploaded_files_data = []
        self.update_uploaded_files_timer = QTimer()
        self.update_uploaded_files_timer.timeout.connect(self.launch_update_uploads_thread)
        self.update_uploaded_files_timer.setInterval(1000)
        self.update_uploaded_files_timer.start()

        self.is_uploading = False
        self.upload_thread_task = None

    # # # # # # # # # # # # # # # # # # # #
    # Funções de lançamento de threads

    def launch_update_uploads_thread(self):
        thread_task = self.UpdatePastUploads(self)
        thread_task.signal_update_past_uploads.connect(self.update_past_downloads_list)
        thread_task.start()

    def button_upload_clicked(self):
        if not self.is_uploading:
            self.start_upload()
        else:
            self.cancel_upload()

    def start_upload(self):
        if not self.selected_file:
            return
        selected_filename = os.path.basename(self.selected_file)
        self.label_drop_file.setText(f'Fazendo upload de\n{selected_filename}...')
        self.progress_bar_upload.setValue(0)

        self.is_uploading = True
        self.set_file_upload_enabled(False)
        self.button_upload.setText('Cancelar upload')

        self.upload_thread_task = self.DoUpload(self)
        self.upload_thread_task.signal_update_progress_bar.connect(self.update_progress_bar)
        self.upload_thread_task.signal_upload_finished.connect(self.upload_finished)
        self.upload_thread_task.start()

    def cancel_upload(self):
        self.is_uploading = False
        self.upload_thread_task.upload_cancelled = True
        self.set_file_upload_enabled(True)
        self.button_upload.setText('Fazer upload')

    # # # # # # # # # # # # # # # # # # # #
    # Funções de atualização da interface

    def update_past_downloads_list(self, new_list: List) -> None:
        if new_list != self.uploaded_files_data:
            self.uploaded_files_data = new_list
            new_list_model = QStringListModel(new_list)
            self.list_past_uploads.setModel(new_list_model)

    def update_progress_bar(self, val: int) -> None:
        self.progress_bar_upload.setValue(val)

    def upload_finished(self, val: str) -> None:
        self.is_uploading = False
        self.button_upload.setText('Fazer upload')

        self.set_file_upload_enabled(True)
        self.label_drop_file.setText(val)

    def set_file_upload_enabled(self, enabled: bool) -> None:
        self.setAcceptDrops(enabled)
        self.label_drop_file.setEnabled(enabled)
        self.button_select_file.setEnabled(enabled)

    def update_selected_file(self) -> None:
        selected_filename = os.path.basename(self.selected_file)
        self.label_drop_file.setText(selected_filename)
        self.progress_bar_upload.setValue(0)

    # # # # # # # # # # # # # # # # # # # #
    # Funções executadas em threads

    class DoUpload(QThread):
        signal_update_progress_bar = Signal(int)
        signal_upload_finished = Signal(str)

        def __init__(self, parent):
            super().__init__(parent)
            self.upload_cancelled = False

        # Callback de atualização da barra de progresso e verificação de cancelamento
        def upload_progress_callback(self, monitor: MultipartEncoderMonitor) -> None:
            # Mandamos um sinal pra barra de progresso para que atualize o valor mostrado
            # baseado na quantidade de bytes lidos e faltantes
            val = int(100 * monitor.bytes_read / monitor.len)
            self.signal_update_progress_bar.emit(val)

            # Se a flag de upload cancelado for ativada, então cancelamos a requisição trocando
            # o método read do MultipartEncoder por uma função que simplesmente levanta a exceção
            # UploadCancelledError. Em seguida, basta tratar da exceção como se fosse um erro de
            # conexão.
            if self.upload_cancelled:
                def cancel_upload(*args, **kwargs):
                    raise UploadCancelledError

                monitor.read = cancel_upload

        def run(self) -> None:
            log.info(f'Starting upload thread...')

            parent = self.parent()
            selected_filename = os.path.basename(parent.selected_file)

            # O requests por padrão não disponibiliza um jeito de rastrear o progresso de upload.
            # Por isso, utilizamos o MultipartEncoderMonitor do requests-toolbelt, que nos permite
            # setar um callback que é chamado quando há uma atualização, e por sua vez emite um sinal
            # que atualiza a ProgressBar de modo não-blocante.
            with open(parent.selected_file, 'rb') as fd:
                # Criamos o MultipartEncoderMonitor
                monitor = MultipartEncoderMonitor.from_fields(
                    fields={'file': (selected_filename, fd, 'text/plain')},
                    callback=self.upload_progress_callback)

                # Fazemos a requisição
                try:
                    r = parent.session.post(f'{server_endpoint}/upload', data=monitor,
                                            headers={'Content-Type': monitor.content_type})
                except requests.exceptions.ConnectionError:
                    log.info(f'Upload failed for {selected_filename}: connection to server failed.')
                    result_message = 'Conexão com o servidor perdida.'
                    self.signal_upload_finished.emit(result_message)
                    return
                except UploadCancelledError:
                    log.info(f'Upload for {selected_filename} cancelled.')
                    result_message = f'Upload cancelado:\n{selected_filename}'
                    self.signal_upload_finished.emit(result_message)
                    return

            # Determinamos a mensagem a ser mostrada e emitimos o sinal de upload concluído.
            if r.status_code == 200:
                log.info(f'Successfully uploaded {selected_filename}')
                result_message = f'Upload concluído:\n{selected_filename}'
            elif r.status_code == 409:
                log.info(f'Failed to upload {selected_filename}: file already exists in remote server (409).')
                result_message = f'Conflito:\nArquivo {selected_filename} já existe.'
            else:
                log.info(f'Failed to upload {selected_filename}: ({r.status_code})\n{r.json()}')
                result_message = f'({r.status_code}) Houve um erro no upload de\n{selected_filename}'
            self.signal_upload_finished.emit(result_message)

    # Thread de update dos arquivos já existentes mostrados à direita
    class UpdatePastUploads(QThread):
        signal_update_past_uploads = Signal(list)

        def run(self) -> None:
            parent = self.parent()

            # Não continuar se não estivermos logados
            if 'Authorization' not in parent.session.cookies:
                return

            # Fazer requisição à rota que disponibiliza informação de arquivos existentes
            r = parent.session.get(f'{server_endpoint}/files')
            existing_files = r.json()
            lines = []
            for file in existing_files:
                dt = datetime.fromisoformat(file["uploaded_at"])
                dt_str = dt.strftime('%c')
                line = f'{file["filename"]} - enviado por {file["uploaded_by"]} ({dt_str})'
                lines.append(line)

            # Emitir sinal de atualização
            self.signal_update_past_uploads.emit(lines)

    # # # # # # # # # # # # # # # # # # # #
    # Seleção de arquivos de upload (botão e arrastar)

    def pick_file(self) -> None:
        path_to_file, _ = QFileDialog.getOpenFileName(self, 'Selecionar arquivo de upload...')
        self.selected_file = path_to_file
        self.update_selected_file()

    # Aceitar drop (mostrar ícone de cópia no arquivo arrastado) somente quando estiver acima da Label de cópia
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self.childAt(event.pos()) is self.label_drop_file:
            event.accept()

    # Atualizar arquivo selecionado quando houver seleção via arquivo arrastado
    def dropEvent(self, event: QDropEvent) -> None:
        mime_dict = {}
        for format in event.mimeData().formats():
            mime_dict[format] = event.mimeData().data(format)
        file_path_bytes = mime_dict['application/x-qt-windows-mime;value="FileNameW"']
        file_path = file_path_bytes.data().decode().replace('\x00', '')
        self.selected_file = file_path
        self.update_selected_file()


class UploadCancelledError(Exception):
    pass
