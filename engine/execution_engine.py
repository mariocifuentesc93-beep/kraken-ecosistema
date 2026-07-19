from core.trade_manager import trade_manager


class ExecutionEngine:

    def __init__(self):

        self.running = False

    # ---------------------------------------------------------

    def start(self):

        if self.running:
            return

        self.running = True

        trade_manager.reload()

        print("[ExecutionEngine] Iniciado.")

    # ---------------------------------------------------------

    def stop(self):

        if not self.running:
            return

        self.running = False

        print("[ExecutionEngine] Detenido.")

    # ---------------------------------------------------------

    def execute(
        self,
        signal,
        profile,
        account,
    ):

        if not self.running:

            print("[ExecutionEngine] detenido.")

            return False

        try:

            print()
            print("-" * 60)
            print(f"💼 MT5 -> {account.name}")
            print("-" * 60)

            # -------------------------------------------------
            # Contexto de ejecución
            # -------------------------------------------------

            signal.profile_id = profile.id
            signal.profile_name = profile.name

            signal.mt5_account_id = account.id
            signal.mt5_account_name = account.name

            if hasattr(account, "execution_mode"):
                signal.execution_mode = account.execution_mode

            if hasattr(account, "risk_mode"):
                signal.risk_mode = account.risk_mode

            if hasattr(account, "risk_percent"):
                signal.risk_percent = account.risk_percent

            if hasattr(account, "risk_amount"):
                signal.risk_amount = account.risk_amount

            if hasattr(account, "fixed_lot"):
                signal.fixed_lot = account.fixed_lot

            if hasattr(account, "magic_number"):
                signal.magic = account.magic_number

            if hasattr(account, "comment"):
                signal.comment = account.comment

            if hasattr(account, "deviation"):
                signal.deviation = account.deviation

            return trade_manager.process_signal(
                signal=signal,
                profile=profile,
                account=account,
            )

        except Exception as e:

            print(
                f"[ExecutionEngine] Error ejecutando '{account.name}': {e}"
            )

            return False

    # ---------------------------------------------------------

    def execute_multiple(
        self,
        signal,
        profile,
        accounts,
    ):

        if not self.running:

            return False

        enabled_accounts = [
            account
            for account in accounts
            if getattr(account, "enabled", True)
        ]

        if not enabled_accounts:

            print("[ExecutionEngine] No existen cuentas MT5 habilitadas.")

            return False

        print()
        print("=" * 60)
        print(f"🚀 Ejecutando en {len(enabled_accounts)} cuenta(s)")
        print("=" * 60)

        success = False

        for account in enabled_accounts:

            result = self.execute(
                signal=signal,
                profile=profile,
                account=account,
            )

            if result:
                success = True

        if success:

            print("✅ Ejecución finalizada.")

        else:

            print("⚠ Ninguna cuenta pudo ejecutar la operación.")

        return success


execution_engine = ExecutionEngine()