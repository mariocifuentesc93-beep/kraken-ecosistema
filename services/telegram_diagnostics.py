"""Telegram connectivity diagnostics with no listener or signal processing."""

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from telethon import TelegramClient
except ImportError:
    TelegramClient = None

from repositories.profile_telegram_repository import profile_telegram_channel_repository
from repositories.telegram_account_repository import telegram_account_repository
from repositories.telegram_diagnostics_repository import telegram_diagnostics_repository


class TelegramDiagnostics:
    NOT_CONFIGURED = "NOT_CONFIGURED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CODE_REQUIRED = "CODE_REQUIRED"
    PASSWORD_REQUIRED = "PASSWORD_REQUIRED"
    AUTHORIZED = "AUTHORIZED"
    ERROR = "ERROR"

    def __init__(self, client_factory=None, package_available=None):
        self.client_factory = TelegramClient if client_factory is None else client_factory
        self.package_available = package_available
        self.clients = {}

    def _package_available(self):
        return self.package_available if self.package_available is not None else (
            self.client_factory is not None and importlib.util.find_spec("telethon") is not None
        )

    @staticmethod
    def _mask_phone(phone):
        digits = "".join(char for char in (phone or "") if char.isdigit())
        return "***" + digits[-4:] if digits else ""

    @staticmethod
    def _session_path(account):
        path = Path(getattr(account, "session_name", "") or "telegram")
        return path if path.suffix == ".session" else Path(str(path) + ".session")

    def _report(self, account, status, success=False, error=""):
        return {
            "account_id": getattr(account, "id", None), "success": success, "status": status,
            "api_id_configured": bool(getattr(account, "api_id", 0)),
            "api_hash_configured": bool(getattr(account, "api_hash", "")),
            "session_path": str(self._session_path(account)), "phone_masked": self._mask_phone(getattr(account, "phone", "")),
            "connected": False, "authorized": False, "user_id": None, "username": "",
            "account_name": "", "session_healthy": False, "last_error": error,
            "connected_timestamp": datetime.now(timezone.utc).isoformat(), "channels": [],
        }

    def _client(self, account):
        if account.id not in self.clients:
            self.clients[account.id] = self.client_factory(account.session_name, int(account.api_id), account.api_hash)
        return self.clients[account.id]

    async def test_connection(self, account, timeout=10):
        report = self._report(account, self.CONNECTING)
        if not self._package_available():
            return self._persist(account, report, self.NOT_CONFIGURED, "El paquete telethon no está instalado.")
        if not account or not account.api_id or not account.api_hash:
            return self._persist(account, report, self.NOT_CONFIGURED, "Configure API ID y API hash de Telegram.")
        try:
            client = self._client(account)
            if not client.is_connected():
                await client.connect()
            report["connected"] = bool(client.is_connected())
            authorized = bool(await client.is_user_authorized())
            report["authorized"] = authorized
            report["session_healthy"] = report["connected"]
            if not authorized:
                return self._persist(account, report, self.CODE_REQUIRED, "Se requiere código de autorización.")
            user = await client.get_me()
            report.update({"user_id": getattr(user, "id", None), "username": getattr(user, "username", "") or "",
                           "account_name": " ".join(filter(None, [getattr(user, "first_name", ""), getattr(user, "last_name", "")])),
                           "channels": await self.validate_channels(account, client)})
            return self._persist(account, report, self.AUTHORIZED)
        except Exception as error:
            return self._persist(account, report, self.ERROR, f"No se pudo conectar con Telegram: {error}")

    async def start_authorization(self, account):
        report = self._report(account, self.CONNECTING)
        if not self._package_available() or not getattr(account, "phone", ""):
            return self._persist(account, report, self.NOT_CONFIGURED, "Configure Telethon y el número telefónico.")
        try:
            client = self._client(account)
            if not client.is_connected():
                await client.connect()
            await client.send_code_request(account.phone)
            report["connected"] = True
            return self._persist(account, report, self.CODE_REQUIRED, "Código enviado; introdúzcalo para verificar.")
        except Exception as error:
            return self._persist(account, report, self.ERROR, f"No se pudo solicitar el código: {error}")

    async def verify_code(self, account, code, password=None):
        report = self._report(account, self.CONNECTING)
        try:
            client = self._client(account)
            if not client.is_connected():
                await client.connect()
            try:
                await client.sign_in(account.phone, code)
            except Exception as error:
                if error.__class__.__name__ == "SessionPasswordNeededError":
                    if not password:
                        return self._persist(account, report, self.PASSWORD_REQUIRED, "La cuenta requiere contraseña de dos pasos.")
                    await client.sign_in(password=password)
                else:
                    raise
            return await self.test_connection(account)
        except Exception as error:
            return self._persist(account, report, self.ERROR, f"Código o contraseña inválidos: {error}")

    async def validate_channels(self, account, client=None):
        client = client or self._client(account)
        results = []
        for channel in profile_telegram_channel_repository.get_channels():
            if channel["account_id"] != account.id:
                continue
            try:
                entity = await client.get_entity(channel["chat_id"])
                title = getattr(entity, "title", "") or channel.get("title", "")
                accessible, error = True, ""
            except Exception as exc:
                title, accessible, error = channel.get("title", ""), False, str(exc)
            results.append({"channel_id": channel["id"], "chat_id": channel["chat_id"], "title": title,
                            "accessible": accessible, "account_has_access": accessible,
                            "enabled": bool(channel["enabled"]), "last_error": error})
        return results

    async def disconnect(self, account):
        client = self.clients.get(account.id)
        if client and client.is_connected():
            await client.disconnect()
        report = self._report(account, self.DISCONNECTED)
        report["authorized"] = bool(getattr(account, "authorized", False))
        return self._persist(account, report, self.DISCONNECTED)

    async def delete_local_session(self, account):
        await self.disconnect(account)
        if not getattr(account, "session_name", ""):
            report = self._report(account, self.DISCONNECTED)
            return self._persist(account, report, self.DISCONNECTED, "No hay una ruta de sesión configurada para eliminar.")
        path = self._session_path(account).resolve()
        if path.exists() and path.is_file():
            path.unlink()
        self.clients.pop(account.id, None)
        report = self._report(account, self.DISCONNECTED)
        report["last_error"] = "Sesión local eliminada."
        return self._persist(account, report, self.DISCONNECTED)

    def _persist(self, account, report, status, error=""):
        report["status"], report["success"], report["last_error"] = status, status == self.AUTHORIZED, error
        account.connected = bool(report["connected"])
        account.authorized = bool(report["authorized"])
        account.last_error = error
        account.user_id, account.username = report["user_id"], report["username"]
        account.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if account.id is not None:
            telegram_account_repository.update(account)
        diagnostic_id = telegram_diagnostics_repository.save_diagnostic(report)
        if report["channels"]:
            telegram_diagnostics_repository.save_channel_results(diagnostic_id, report["channels"])
        report["diagnostic_id"] = diagnostic_id
        return report

    @staticmethod
    def to_json(report):
        return json.dumps(report, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def to_text(report):
        fields = ("status", "session_path", "phone_masked", "connected", "authorized", "user_id", "username", "session_healthy", "connected_timestamp", "last_error")
        return "Telegram Diagnostics\n" + "\n".join(f"{field}: {report.get(field, '')}" for field in fields) + f"\nChannels: {len(report.get('channels', []))}"

    def export_json(self, report, destination):
        Path(destination).write_text(self.to_json(report), encoding="utf-8")

    def export_text(self, report, destination):
        Path(destination).write_text(self.to_text(report), encoding="utf-8")


telegram_diagnostics = TelegramDiagnostics()
