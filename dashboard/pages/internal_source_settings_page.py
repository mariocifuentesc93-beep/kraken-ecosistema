import asyncio

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dashboard.widgets.section_widget import SectionWidget
from repositories.internal_publication_config_repository import (
    internal_publication_config_repository,
)
from repositories.profile_telegram_repository import (
    profile_telegram_channel_repository,
)
from services.internal_publication_configuration_service import (
    InternalPublicationConfigurationService,
)
from telegram.account_manager import telegram_account_manager


class InternalSourceSettingsPage(QWidget):
    """Single global configuration point for Inspector INTERNAL publication."""

    def __init__(
        self,
        config_repository=None,
        account_manager=None,
        destinations_provider=None,
        test_sender=None,
        parent=None,
    ):
        super().__init__(parent)
        self._config_repository = (
            config_repository or internal_publication_config_repository
        )
        self._account_manager = account_manager or telegram_account_manager
        self._destinations_provider = (
            destinations_provider
            or profile_telegram_channel_repository.get_available_channels
        )
        self._test_sender = test_sender or self._send_test_message
        self._destinations = {}
        self._service = InternalPublicationConfigurationService(
            repository=self._config_repository,
            account_provider=self._account_manager.get_account,
            destinations_provider=self._destinations_provider,
        )
        self._build_ui()
        self.load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        section = SectionWidget("Internal Signal Source")
        form = QGridLayout()

        self.publish_checkbox = QCheckBox(
            "Publicar señales INTERNAL en Telegram"
        )
        self.account_combo = QComboBox()
        self.destination_combo = QComboBox()
        self.destination_name = QLabel("-")
        self.destination_type = QLabel("-")
        self.chat_id_label = QLabel("-")
        self.test_button = QPushButton("Probar envío")
        self.save_button = QPushButton("Guardar configuración")
        self.reload_button = QPushButton("Recargar")

        form.addWidget(self.publish_checkbox, 0, 0, 1, 2)
        for row, (label, widget) in enumerate(
            (
                ("Cuenta Telegram", self.account_combo),
                ("Destino", self.destination_combo),
                ("Nombre", self.destination_name),
                ("Tipo", self.destination_type),
                ("Chat ID", self.chat_id_label),
            ),
            start=1,
        ):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(widget, row, 1)
        form.setColumnStretch(1, 1)
        section.addLayout(form)
        layout.addWidget(section)

        buttons = QHBoxLayout()
        buttons.addWidget(self.test_button)
        buttons.addStretch()
        buttons.addWidget(self.reload_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)
        layout.addStretch()

        self.publish_checkbox.toggled.connect(self._update_enabled)
        self.account_combo.currentIndexChanged.connect(
            lambda *_: self._load_destinations()
        )
        self.destination_combo.currentIndexChanged.connect(
            self._show_destination
        )
        self.reload_button.clicked.connect(self.load)
        self.save_button.clicked.connect(self.save)
        self.test_button.clicked.connect(self.test_send)

    @staticmethod
    def _destination_type(item):
        explicit = str(
            item.get("type") or item.get("entity_type") or ""
        ).strip()
        if explicit:
            return explicit
        return "Canal" if item.get("username") else "Grupo"

    def _accounts(self):
        self._account_manager.reload()
        return self._account_manager.get_accounts()

    def _load_accounts(self, selected=None):
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        self.account_combo.addItem("Seleccione una cuenta", None)
        for account in self._accounts():
            self.account_combo.addItem(account.display_name, account.id)
        index = self.account_combo.findData(selected)
        self.account_combo.setCurrentIndex(max(0, index))
        self.account_combo.blockSignals(False)

    def _load_destinations(self, selected=None):
        account_id = self.account_combo.currentData()
        if selected is None:
            selected = self.destination_combo.currentData()
        self.destination_combo.blockSignals(True)
        self.destination_combo.clear()
        self.destination_combo.addItem("Seleccione un chat o canal", None)
        self._destinations = {}
        if account_id is not None:
            for item in self._destinations_provider(account_id):
                chat_id = int(item["chat_id"])
                title = (
                    item.get("title")
                    or item.get("name")
                    or item.get("username")
                    or str(chat_id)
                )
                destination_type = self._destination_type(item)
                normalized = {
                    **item,
                    "chat_id": chat_id,
                    "title": title,
                    "type": destination_type,
                }
                self._destinations[chat_id] = normalized
                self.destination_combo.addItem(
                    f"{title} · {destination_type} · {chat_id}",
                    chat_id,
                )
        index = self.destination_combo.findData(selected)
        self.destination_combo.setCurrentIndex(max(0, index))
        self.destination_combo.blockSignals(False)
        self._show_destination()

    def _show_destination(self, *_):
        item = self._destinations.get(
            self.destination_combo.currentData()
        )
        self.destination_name.setText(item["title"] if item else "-")
        self.destination_type.setText(item["type"] if item else "-")
        self.chat_id_label.setText(
            str(item["chat_id"]) if item else "-"
        )

    def _update_enabled(self, enabled):
        self.account_combo.setEnabled(enabled)
        self.destination_combo.setEnabled(enabled)
        self.test_button.setEnabled(enabled)

    def load(self):
        config = self._service.get()
        self._load_accounts(config.telegram_account_id)
        self._load_destinations(config.telegram_output_chat_id)
        self.publish_checkbox.setChecked(config.enabled)
        self._update_enabled(config.enabled)

    def save(self):
        try:
            self._service.save(
                self.publish_checkbox.isChecked(),
                self.account_combo.currentData(),
                self.destination_combo.currentData(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Inspector INTERNAL", str(error))
            return False
        QMessageBox.information(
            self,
            "Inspector INTERNAL",
            "Configuración global guardada.",
        )
        return True

    async def _send_test_async(self, account_id, chat_id):
        client = await self._account_manager.connect(account_id)
        await client.send_message(
            chat_id,
            "Kraken INTERNAL: mensaje de prueba.",
        )

    def _send_test_message(self, account_id, chat_id):
        asyncio.run(self._send_test_async(account_id, chat_id))

    def test_send(self):
        account_id = self.account_combo.currentData()
        chat_id = self.destination_combo.currentData()
        try:
            self._service.validate(True, account_id, chat_id)
            self._test_sender(account_id, chat_id)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Prueba Telegram",
                f"No se pudo enviar el mensaje de prueba: {error}",
            )
            return False
        QMessageBox.information(
            self,
            "Prueba Telegram",
            "Mensaje de prueba enviado correctamente.",
        )
        return True
