from datetime import datetime

from models.operation import Operation

from repositories.operation_repository import (
    operation_repository,
)

from trading.operation_events import (
    operation_events,
)

from core.event_bus import event_bus

from core.events import (
    OperationCreatedEvent,
    OperationOpenedEvent,
    OperationModifiedEvent,
    OperationClosedEvent,
)


class OperationManager:

    # =====================================================
    # CREATE
    # =====================================================

    def create(
        self,
        signal,
        profile,
        account,
    ):

        operation = Operation(
            signal=signal,
            profile=profile,
            account=account,
        )

        now = datetime.now()

        operation.created_at = now
        operation.updated_at = now
        operation.status = "CREATED"

        operation_repository.add(operation)

        operation_events.operation_created(operation)

        event_bus.operationCreated.emit(
            OperationCreatedEvent(
                operation=operation,
            )
        )

        print()
        print("=" * 60)
        print("🆕 OPERACIÓN CREADA")
        print("=" * 60)
        print(f"Perfil : {profile.name}")
        print(f"Cuenta : {account.name}")
        print(f"ID     : {operation.id}")

        return operation

    # =====================================================
    # OPEN
    # =====================================================

    def open(
        self,
        operation,
        ticket,
        volume,
        position_id=0,
    ):

        operation.ticket = ticket
        operation.position_id = position_id
        operation.volume = volume

        operation.status = "OPEN"

        operation.opened_at = datetime.now()
        operation.updated_at = datetime.now()

        operation_repository.update(operation)

        operation_events.operation_opened(operation)

        event_bus.operationOpened.emit(
            OperationOpenedEvent(
                operation=operation,
            )
        )

        try:
            event_bus.notify(
                f"Operación abierta. Ticket {ticket}"
            )
        except Exception:
            pass

        try:
            event_bus.refresh_dashboard()
        except Exception:
            pass

        print(f"✅ Operación abierta ({ticket})")

    # =====================================================
    # CLOSE
    # =====================================================

    def close(
        self,
        operation,
        reason,
        profit=0.0,
    ):

        operation.status = "CLOSED"

        operation.close_reason = reason
        operation.profit = profit

        operation.closed_at = datetime.now()
        operation.updated_at = datetime.now()

        if profit > 0:
            operation.result = "WIN"
        elif profit < 0:
            operation.result = "LOSS"
        else:
            operation.result = "BREAKEVEN"

        operation_repository.update(operation)

        operation_events.operation_closed(operation)

        event_bus.operationClosed.emit(
            OperationClosedEvent(
                operation=operation,
                profit=profit,
            )
        )

        try:
            event_bus.update_profit(profit)
        except Exception:
            pass

        try:
            event_bus.update_statistics()
        except Exception:
            pass

        try:
            event_bus.refresh_dashboard()
        except Exception:
            pass

        print()
        print("=" * 60)
        print("📈 OPERACIÓN CERRADA")
        print("=" * 60)
        print(f"Resultado : {operation.result}")
        print(f"Profit    : {profit}")
        print(f"Motivo    : {reason}")

    # =====================================================
    # UPDATE
    # =====================================================

    def update(
        self,
        operation,
    ):

        operation.updated_at = datetime.now()

        operation_repository.update(operation)

        event_bus.operationModified.emit(
            OperationModifiedEvent(
                operation=operation,
            )
        )

        try:
            event_bus.refresh_dashboard()
        except Exception:
            pass

    # =====================================================
    # DELETE
    # =====================================================

    def remove(
        self,
        operation,
    ):

        operation_repository.remove(
            operation.id
        )

    # =====================================================
    # GETTERS
    # =====================================================

    def get(
        self,
        operation_id,
    ):

        return operation_repository.get(operation_id)

    def get_all(self):

        return operation_repository.get_all()

    def get_open(self):

        return operation_repository.get_open()

    def get_closed(self):

        return operation_repository.get_closed()


operation_manager = OperationManager()
