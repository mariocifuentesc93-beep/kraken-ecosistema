from datetime import datetime

from models.operation import Operation
from repositories.operation_repository import operation_repository
from repositories.log_repository import log_repository


class SimulationEngine:

    def __init__(self):

        self.running = True

    # =====================================================
    # EJECUTAR SEÑAL
    # =====================================================

    def execute(self, signal, profile, account, operation=None):

        if operation is None:
            operation = Operation(
                signal=signal,
                profile=profile,
                account=account,
            )

            operation_repository.add(operation)

        operation.signal_id = getattr(signal, "id", None)
        operation.profile_id = signal.profile_id

        operation.telegram_account_id = getattr(
            signal,
            "telegram_account_id",
            None,
        )

        operation.account_id = account.id
        operation.mt5_account_id = account.id

        operation.symbol = signal.symbol
        operation.direction = signal.direction

        operation.volume = getattr(
            account,
            "fixed_lot",
            0.10,
        )

        operation.entry = signal.entry
        operation.entry_price = signal.entry

        operation.stop_loss = signal.stop_loss
        operation.take_profit = signal.tp1

        operation.magic_number = getattr(
            account,
            "custom_magic",
            0,
        ) or getattr(
            account,
            "magic_number",
            10001,
        )

        operation.comment = getattr(
            account,
            "comment",
            "SIMULATION",
        )

        operation.ticket = 0

        operation.status = "SIMULATION"

        operation.result = "OPEN"

        operation.profit = 0.0

        operation.opened_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        operation_repository.update(operation)

        log_repository.info(
            "SimulationEngine",
            (
                f"Simulación creada | "
                f"{operation.symbol} | "
                f"{operation.direction} | "
                f"Cuenta {account.name}"
            ),
        )

        return operation

    # =====================================================
    # CERRAR
    # =====================================================

    def close_operation(
        self,
        operation,
        exit_price,
        profit,
        result,
    ):

        operation.exit_price = exit_price

        operation.profit = profit

        operation.result = result

        operation.status = "CLOSED"

        operation.closed_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        operation_repository.update(operation)

        log_repository.info(
            "SimulationEngine",
            (
                f"Simulación cerrada | "
                f"Ticket {operation.ticket} | "
                f"{profit:.2f}"
            ),
        )

        return operation

    # =====================================================
    # CANCELAR
    # =====================================================

    def cancel(self, operation):

        operation.status = "CANCELLED"

        operation.closed_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        operation_repository.update(operation)

        log_repository.warning(
            "SimulationEngine",
            f"Simulación cancelada {operation.symbol}",
        )

    # =====================================================
    # RESET
    # =====================================================

    def reset(self):

        log_repository.info(
            "SimulationEngine",
            "Motor de simulación reiniciado",
        )


simulation_engine = SimulationEngine()
