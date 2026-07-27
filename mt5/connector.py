import os
import time

import MetaTrader5 as mt5


class MT5Connector:
    """Connection-only MT5 adapter. It never creates or modifies trades."""

    def __init__(self):
        self.connected = False
        self.connecting = False
        self.current_account = None
        self.account = None
        self.last_error = ""

    def _error(self, message):
        self.connected = False
        self.last_error = message
        return False

    @staticmethod
    def _credentials_are_complete(account):
        return bool(
            account
            and getattr(account, "login", 0)
            and getattr(account, "password", "")
            and getattr(account, "server", "")
        )

    @staticmethod
    def _same_terminal_path(current_path, expected_path):
        if not isinstance(current_path, str) or not current_path.strip():
            return None
        if not isinstance(expected_path, str) or not expected_path.strip():
            return None
        def normalized(value):
            path = os.path.abspath(value)
            if os.path.splitext(path)[1].lower() == ".exe":
                path = os.path.dirname(path)
            return os.path.normcase(path)

        return normalized(current_path) == normalized(expected_path)

    def connect(self, account, timeout_ms=10_000, retries=2):
        if account is None:
            return self._error("No se seleccionó una cuenta MT5.")
        self.connecting = True
        self.account = account
        terminal = getattr(account, "terminal_path", "")
        try:
            terminal_info = mt5.terminal_info()
            current_path = getattr(terminal_info, "path", None)
            same_terminal = self._same_terminal_path(current_path, terminal)
            if same_terminal is False:
                # Detach only the Python integration.  This does not close the
                # running terminal and lets initialize() bind the requested one.
                mt5.shutdown()

            for attempt in range(retries + 1):
                kwargs = {"timeout": timeout_ms}
                if terminal:
                    kwargs["path"] = terminal
                if mt5.initialize(**kwargs):
                    initialized_info = mt5.terminal_info()
                    initialized_path = getattr(initialized_info, "path", None)
                    initialized_matches = self._same_terminal_path(
                        initialized_path, terminal
                    )
                    if initialized_matches is False:
                        self.last_error = (
                            "MT5 se vinculó a una terminal distinta de la "
                            "configurada para la cuenta."
                        )
                        mt5.shutdown()
                        if attempt < retries:
                            time.sleep(0.25 * (attempt + 1))
                            continue
                        return self._error(self.last_error)
                    self.connected = True
                    self.last_error = ""
                    return True
                self.last_error = f"MT5 no respondió: {mt5.last_error()}"
                if attempt < retries:
                    time.sleep(0.25 * (attempt + 1))
            return self._error(self.last_error)
        finally:
            self.connecting = False

    def login(self, account, timeout_ms=10_000, retries=2):
        if not self._credentials_are_complete(account):
            return self._error("Faltan login, contraseña o servidor de MT5.")
        if not self.connect(account, timeout_ms, retries):
            return False

        login = int(account.login)
        if self.current_account == login and self.is_connected():
            return True

        for attempt in range(retries + 1):
            if mt5.login(
                login=login,
                password=account.password,
                server=account.server,
                timeout=timeout_ms,
            ):
                self.current_account = login
                self.connected = True
                self.last_error = ""
                self.refresh_account(account)
                return True
            self.last_error = f"Credenciales MT5 rechazadas: {mt5.last_error()}"
            if attempt < retries:
                time.sleep(0.25 * (attempt + 1))
        return self._error(self.last_error)

    def test_connection(self, account, timeout_ms=10_000, retries=2):
        connected = self.login(account, timeout_ms, retries)
        return connected, self.last_error if not connected else "Conexión MT5 verificada."

    def disconnect(self):
        mt5.shutdown()
        self.connected = False
        self.connecting = False
        self.current_account = None
        self.account = None
        self.last_error = ""

    def is_connected(self):
        terminal_info = mt5.terminal_info()
        account_info = mt5.account_info() if terminal_info is not None else None
        expected_login = int(
            getattr(self.account, "login", 0) or 0
        )
        detected_login = int(
            getattr(account_info, "login", 0) or 0
        )
        self.connected = bool(
            terminal_info is not None
            and account_info is not None
            and expected_login > 0
            and detected_login == expected_login
        )
        if self.connected:
            self.current_account = detected_login
        return self.connected

    def get_account_info(self):
        return mt5.account_info()

    def refresh_account(self, account):
        info = self.get_account_info()
        if info is None:
            return False
        account.balance = info.balance
        account.equity = info.equity
        account.free_margin = info.margin_free
        account.connected = True
        return True

    def get_balance(self):
        info = self.get_account_info()
        return info.balance if info else 0.0

    def get_equity(self):
        info = self.get_account_info()
        return info.equity if info else 0.0

    def get_free_margin(self):
        info = self.get_account_info()
        return info.margin_free if info else 0.0

    def get_symbol_info(self, symbol):
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        if not info.visible:
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
        return info

    def get_tick(self, symbol):
        return mt5.symbol_info_tick(symbol)

    def get_digits(self, symbol):
        info = self.get_symbol_info(symbol)
        return info.digits if info else 0

    def get_point_value(self, symbol):
        info = self.get_symbol_info(symbol)
        return info.point if info else None

    def get_contract_size(self, symbol):
        info = self.get_symbol_info(symbol)
        return info.trade_contract_size if info else None

    def get_volume_min(self, symbol):
        info = self.get_symbol_info(symbol)
        return info.volume_min if info else 0.01

    def get_volume_max(self, symbol):
        info = self.get_symbol_info(symbol)
        return info.volume_max if info else 100.0

    def get_volume_step(self, symbol):
        info = self.get_symbol_info(symbol)
        return info.volume_step if info else 0.01

    def symbol_exists(self, symbol):
        return self.get_symbol_info(symbol) is not None


mt5_connector = MT5Connector()
