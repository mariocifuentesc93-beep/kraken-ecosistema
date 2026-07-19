import MetaTrader5 as mt5


class MT5Connector:

    def __init__(self):

        self.connected = False
        self.current_account = None

    # ---------------------------------------------------------

    def connect(self, account):

        if self.is_connected():

            return True

        terminal = getattr(account, "terminal_path", "")

        if terminal:

            ok = mt5.initialize(path=terminal)

        else:

            ok = mt5.initialize()

        if not ok:

            print(f"[MT5] Error initialize: {mt5.last_error()}")

            self.connected = False

            return False

        self.connected = True

        return True

    # ---------------------------------------------------------

    def login(self, account):

        if account is None:

            print("[MT5] Cuenta MT5 no especificada.")

            return False

        if not self.connect(account):

            return False

        login = int(account.login)

        if (
            self.current_account == login
            and self.is_connected()
        ):

            return True

        ok = mt5.login(
            login=login,
            password=account.password,
            server=account.server,
        )

        if not ok:

            print(f"[MT5] Login incorrecto: {mt5.last_error()}")

            self.connected = False

            return False

        self.current_account = login
        self.connected = True

        self.refresh_account(account)

        print()
        print("=" * 60)
        print("✅ MT5 CONECTADO")
        print("=" * 60)
        print(f"Cuenta   : {account.name}")
        print(f"Login    : {account.login}")
        print(f"Servidor : {account.server}")
        print("=" * 60)

        return True

    # ---------------------------------------------------------

    def disconnect(self):

        mt5.shutdown()

        self.connected = False
        self.current_account = None

    # ---------------------------------------------------------

    def is_connected(self):

        return mt5.terminal_info() is not None

    # ---------------------------------------------------------

    def get_account_info(self):

        return mt5.account_info()

    # ---------------------------------------------------------

    def refresh_account(self, account):

        info = self.get_account_info()

        if info is None:

            return False

        try:

            account.balance = info.balance
            account.equity = info.equity
            account.free_margin = info.margin_free
            account.margin = info.margin
            account.connected = True

        except Exception:

            pass

        return True

    # ---------------------------------------------------------

    def get_balance(self):

        info = self.get_account_info()

        return info.balance if info else 0.0

    # ---------------------------------------------------------

    def get_equity(self):

        info = self.get_account_info()

        return info.equity if info else 0.0

    # ---------------------------------------------------------

    def get_free_margin(self):

        info = self.get_account_info()

        return info.margin_free if info else 0.0

    # ---------------------------------------------------------

    def get_symbol_info(self, symbol):

        info = mt5.symbol_info(symbol)

        if info is None:

            return None

        if not info.visible:

            mt5.symbol_select(symbol, True)

            info = mt5.symbol_info(symbol)

        return info

    # ---------------------------------------------------------

    def get_tick(self, symbol):

        return mt5.symbol_info_tick(symbol)

    # ---------------------------------------------------------

    def get_digits(self, symbol):

        info = self.get_symbol_info(symbol)

        return info.digits if info else 0

    # ---------------------------------------------------------

    def get_point_value(self, symbol):

        info = self.get_symbol_info(symbol)

        return info.point if info else None

    # ---------------------------------------------------------

    def get_contract_size(self, symbol):

        info = self.get_symbol_info(symbol)

        return info.trade_contract_size if info else None

    # ---------------------------------------------------------

    def get_volume_min(self, symbol):

        info = self.get_symbol_info(symbol)

        return info.volume_min if info else 0.01

    # ---------------------------------------------------------

    def get_volume_max(self, symbol):

        info = self.get_symbol_info(symbol)

        return info.volume_max if info else 100.0

    # ---------------------------------------------------------

    def get_volume_step(self, symbol):

        info = self.get_symbol_info(symbol)

        return info.volume_step if info else 0.01

    # ---------------------------------------------------------

    def symbol_exists(self, symbol):

        return self.get_symbol_info(symbol) is not None


mt5_connector = MT5Connector()