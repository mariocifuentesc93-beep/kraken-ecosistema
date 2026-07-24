from copy import deepcopy


class ExecutionEngine:

    def __init__(self, trade_manager_instance=None):
        self.running = False
        self._trade_manager = trade_manager_instance

    def _get_trade_manager(self):
        if self._trade_manager is None:
            from core.trade_manager import trade_manager
            self._trade_manager = trade_manager

        return self._trade_manager

    def start(self):
        if self.running:
            return

        self.running = True
        self._get_trade_manager().reload()
        print("[ExecutionEngine] Iniciado.")

    def stop(self):
        if not self.running:
            return

        self.running = False
        print("[ExecutionEngine] Detenido.")

    def execute(self, signal, profile, account):
        """
        Ejecuta una copia independiente de la señal para una cuenta.

        La inyección de TradeManager permite validar el pipeline sin cargar
        MetaTrader5 ni enviar órdenes reales.
        """

        if not self.running:
            return False

        account_signal = deepcopy(signal)
        account_signal.profile_id = profile.id
        account_signal.profile_name = profile.name
        account_signal.mt5_account_id = account.id
        account_signal.mt5_account_name = account.name
        account_signal.execution_mode = getattr(
            account,
            "execution_mode",
            getattr(account_signal, "execution_mode", None),
        )
        account_signal.risk_mode = getattr(
            account,
            "risk_mode",
            None,
        )
        account_signal.risk_percent = getattr(
            account,
            "risk_percent",
            0.0,
        )
        account_signal.risk_amount = getattr(
            account,
            "risk_amount",
            0.0,
        )
        account_signal.fixed_lot = getattr(
            account,
            "fixed_lot",
            0.0,
        )
        account_signal.magic = getattr(
            account,
            "magic_number",
            0,
        )
        account_signal.comment = getattr(account, "comment", "")
        account_signal.deviation = getattr(account, "deviation", 20)

        try:
            return self._get_trade_manager().process_signal(
                signal=account_signal,
                profile=profile,
                account=account,
            )
        except Exception as error:
            print(
                f"[ExecutionEngine] Error ejecutando "
                f"'{account.name}': {error}"
            )
            return False

    def execute_multiple(self, signal, profile, accounts):
        if not self.running:
            return False

        enabled_accounts = [
            account
            for account in accounts
            if getattr(account, "enabled", True)
        ]

        success = False

        for account in enabled_accounts:
            if self.execute(signal, profile, account):
                success = True

        return success


execution_engine = ExecutionEngine()
