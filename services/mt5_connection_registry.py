"""Account-scoped registry for isolated MetaTrader 5 workers."""

from __future__ import annotations

import threading

from mt5.multi_terminal_connection import (
    MT5TerminalConnection,
    MT5WorkerError,
)


class MT5ConnectionRegistryService:
    """Return one persistent connection per (terminal, account) pair."""

    def __init__(
        self,
        account_provider=None,
        terminal_provider=None,
        connection_factory=None,
    ):
        self._account_provider = account_provider
        self._terminal_provider = terminal_provider
        self._connection_factory = (
            connection_factory or MT5TerminalConnection
        )
        self._connections = {}
        self._lock = threading.RLock()

    def _account(self, account_id):
        if self._account_provider is None:
            from repositories.mt5_account_repository import (
                mt5_account_repository,
            )

            self._account_provider = mt5_account_repository.get_by_id
        return self._account_provider(account_id)

    def _terminal(self, terminal_id):
        if self._terminal_provider is None:
            from repositories.mt5_terminal_repository import (
                mt5_terminal_repository,
            )

            self._terminal_provider = mt5_terminal_repository.get_by_id
        return self._terminal_provider(terminal_id)

    @staticmethod
    def _validate(account, terminal):
        if account is None:
            raise MT5WorkerError("La cuenta MT5 no existe.")
        if terminal is None:
            raise MT5WorkerError(
                "La cuenta no tiene una terminal MT5 válida."
            )
        if not bool(getattr(account, "active", True)):
            raise MT5WorkerError("La cuenta MT5 está deshabilitada.")
        if not bool(getattr(terminal, "active", True)):
            raise MT5WorkerError("La terminal MT5 está deshabilitada.")
        if not bool(getattr(terminal, "can_trade", False)):
            raise MT5WorkerError(
                "La terminal seleccionada no tiene capacidad TRADING."
            )
        linked_terminal = getattr(account, "mt5_terminal_id", None)
        if linked_terminal is None or int(linked_terminal) != int(terminal.id):
            raise MT5WorkerError(
                "La cuenta no está vinculada a la terminal solicitada."
            )
        if not getattr(account, "login", 0):
            raise MT5WorkerError("La cuenta MT5 no tiene login.")
        if not getattr(account, "password", ""):
            raise MT5WorkerError("La cuenta MT5 no tiene contraseña.")
        if not getattr(account, "server", ""):
            raise MT5WorkerError("La cuenta MT5 no tiene servidor.")

    def connection_for(self, mt5_account_id, mt5_terminal_id=None):
        account = self._account(mt5_account_id)
        resolved_terminal_id = (
            mt5_terminal_id
            if mt5_terminal_id is not None
            else getattr(account, "mt5_terminal_id", None)
        )
        terminal = self._terminal(resolved_terminal_id)
        self._validate(account, terminal)
        key = (int(terminal.id), int(account.id))
        with self._lock:
            connection = self._connections.get(key)
            if connection is not None and connection.alive:
                return connection
            if connection is not None:
                connection.close()
            connection = self._connection_factory(account, terminal)
            self._connections[key] = connection
            return connection

    def get(self, mt5_account_id):
        """Compatibility with the account-scoped symbol catalog contract."""
        account = self._account(mt5_account_id)
        if account is None:
            return None
        return self.connection_for(
            account.id,
            getattr(account, "mt5_terminal_id", None),
        )

    def peek(self, mt5_account_id, mt5_terminal_id=None):
        terminal_id = mt5_terminal_id
        if terminal_id is None:
            account = self._account(mt5_account_id)
            terminal_id = getattr(account, "mt5_terminal_id", None)
        if terminal_id is None:
            return None
        return self._connections.get(
            (int(terminal_id), int(mt5_account_id))
        )

    def stop_connection(self, mt5_account_id, mt5_terminal_id=None):
        terminal_id = mt5_terminal_id
        if terminal_id is None:
            account = self._account(mt5_account_id)
            terminal_id = getattr(account, "mt5_terminal_id", None)
        if terminal_id is None:
            return False
        key = (int(terminal_id), int(mt5_account_id))
        with self._lock:
            connection = self._connections.pop(key, None)
        if connection is None:
            return False
        connection.close()
        return True

    def stop_all(self):
        with self._lock:
            connections = list(self._connections.values())
            self._connections.clear()
        for connection in connections:
            connection.close()

    def status(self):
        with self._lock:
            return {
                key: {
                    "alive": connection.alive,
                    "process_id": connection.process_id,
                    "login": connection.login,
                }
                for key, connection in self._connections.items()
            }


mt5_connection_registry = MT5ConnectionRegistryService()
