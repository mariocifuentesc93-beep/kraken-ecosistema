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

    def connect(self, account, timeout_ms=10_000, retries=2):
        if account is None:
            return self._error("No se seleccionó una cuenta MT5.")
        self.connecting = True
        self.account = account
        terminal = getattr(account, "terminal_path", "")
        try:
            for attempt in range(retries + 1):
                kwargs = {"timeout": timeout_ms}
                if terminal:
                    kwargs["path"] = terminal
                if mt5.initialize(**kwargs):
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
        self.connected = mt5.terminal_info() is not None
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
