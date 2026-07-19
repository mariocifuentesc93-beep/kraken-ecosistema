from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)

from dashboard.dialogs.channel_dialog import ChannelDialog
from repositories.profile_repository import profile_repository
from repositories.profile_telegram_repository import profile_telegram_channel_repository


class ChannelsPage(QWidget):

    def __init__(self):
        super().__init__()
        self.build_ui()
        self.refresh()

    def build_ui(self):
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)

        self.btn_new = QPushButton("Nuevo")
        self.btn_edit = QPushButton("Editar")
        self.btn_delete = QPushButton("Eliminar")
        self.btn_refresh = QPushButton("Actualizar")
        for button in (self.btn_new, self.btn_edit, self.btn_delete):
            toolbar.addWidget(button)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Canal", "Chat ID", "Usuario", "Perfil", "Activo", "Prioridad"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.btn_new.clicked.connect(self.new_channel)
        self.btn_edit.clicked.connect(self.edit_channel)
        self.btn_delete.clicked.connect(self.delete_channel)
        self.btn_refresh.clicked.connect(self.refresh)

    def refresh(self):
        channels = profile_telegram_channel_repository.get_channels()
        profiles = {profile.id: profile.name for profile in profile_repository.get_all()}
        self.table.setRowCount(len(channels))
        for row, channel in enumerate(channels):
            values = [
                channel["id"], channel.get("title", ""), channel["chat_id"],
                channel.get("username", ""),
                profiles.get(channel["profile_id"], "Perfil eliminado"),
                "Sí" if channel.get("enabled") else "No", channel.get("priority", 1),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)

    def selected_channel(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return profile_telegram_channel_repository.get_by_id(
            int(self.table.item(row, 0).text())
        )

    def _dialog(self, channel=None):
        profiles = profile_repository.get_all()
        if not profiles:
            QMessageBox.warning(self, "Canales", "Cree un perfil antes de administrar canales.")
            return None
        dialog = ChannelDialog(parent=self)
        dialog.set_profiles(profiles)
        if channel is not None:
            dialog.load_channel(channel)
        return dialog

    def _save_channel(self, dialog, existing=None):
        data = dialog.get_channel_data()
        try:
            chat_id = int(data["chat_id"])
            profile = profile_repository.get_by_id(data["profile"])
            if profile is None or not profile.telegram_account_id:
                raise ValueError("El perfil seleccionado debe tener una cuenta de Telegram asignada.")
            priority = data["priority"] + 1
            if existing is None:
                channel_id = profile_telegram_channel_repository.create_channel(
                    chat_id, data["name"], profile.id, profile.telegram_account_id
                )
            else:
                channel_id = existing["id"]
            profile_telegram_channel_repository.update_channel(
                channel_id, chat_id, data["name"], data["username"], profile.id,
                profile.telegram_account_id, data["enabled"], priority
            )
        except (TypeError, ValueError) as error:
            QMessageBox.critical(self, "Canales", f"No se pudo guardar el canal: {error}")
            return
        self.refresh()

    def new_channel(self):
        dialog = self._dialog()
        if dialog is not None and dialog.exec():
            self._save_channel(dialog)

    def edit_channel(self):
        channel = self.selected_channel()
        if channel is None:
            QMessageBox.warning(self, "Canales", "Seleccione un canal.")
            return
        dialog = self._dialog(channel)
        if dialog is not None and dialog.exec():
            self._save_channel(dialog, channel)

    def delete_channel(self):
        channel = self.selected_channel()
        if channel is None:
            QMessageBox.warning(self, "Canales", "Seleccione un canal.")
            return
        if QMessageBox.question(
            self, "Eliminar canal", f"¿Desea eliminar el canal '{channel.get('title', '')}'?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            profile_telegram_channel_repository.delete_channel(channel["id"])
            self.refresh()
