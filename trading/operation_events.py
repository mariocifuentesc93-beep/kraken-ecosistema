from datetime import datetime

from core.event_bus import event_bus


class OperationEvents:

    # =====================================================
    # LOG
    # =====================================================

    def _log(
        self,
        level,
        message,
    ):

        text = f"[{datetime.now():%H:%M:%S}] {level} {message}"

        print(text)

        try:
            event_bus.log(text)
        except Exception:
            pass

    # =====================================================
    # CREATED
    # =====================================================

    def operation_created(
        self,
        operation,
    ):

        profile = getattr(operation, "profile", None)
        account = getattr(operation, "account", None)
        signal = getattr(operation, "signal", None)

        self._log(
            "🆕",
            (
                f"Operación creada | "
                f"ID={operation.id} | "
                f"Perfil={getattr(profile,'name','-')} | "
                f"Cuenta={getattr(account,'name','-')} | "
                f"Símbolo={getattr(signal,'symbol','-')} | "
                f"Dirección={getattr(signal,'direction','-')}"
            ),
        )

    # =====================================================
    # OPENED
    # =====================================================

    def operation_opened(
        self,
        operation,
    ):

        self._log(
            "✅",
            (
                f"Operación abierta | "
                f"Ticket={operation.ticket} | "
                f"Vol={operation.volume}"
            ),
        )

    # =====================================================
    # CLOSED
    # =====================================================

    def operation_closed(
        self,
        operation,
    ):

        profit = getattr(operation, "profit", 0.0)

        self._log(
            "❌",
            (
                f"Operación cerrada | "
                f"Ticket={getattr(operation,'ticket',0)} | "
                f"Profit={profit:.2f} | "
                f"Resultado={getattr(operation,'result','')} | "
                f"Motivo={getattr(operation,'close_reason','')}"
            ),
        )

        if profit > 0:

            self.operation_profit(operation)

        elif profit < 0:

            self.operation_loss(operation)

        else:

            self.operation_breakeven(operation)

    # =====================================================
    # RESULTADOS
    # =====================================================

    def operation_profit(
        self,
        operation,
    ):

        self._log(
            "📈",
            f"WIN | Ticket={operation.ticket} | +{operation.profit:.2f}",
        )

    def operation_loss(
        self,
        operation,
    ):

        self._log(
            "📉",
            f"LOSS | Ticket={operation.ticket} | {operation.profit:.2f}",
        )

    def operation_breakeven(
        self,
        operation,
    ):

        self._log(
            "➖",
            f"BREAKEVEN | Ticket={operation.ticket}",
        )

    # =====================================================
    # EVENTOS FUTUROS
    # =====================================================

    def break_even_enabled(
        self,
        operation,
    ):

        self._log(
            "🟦",
            f"Break Even | Ticket={operation.ticket}",
        )

        try:
            event_bus.notify(
                f"Break Even activado ({operation.ticket})"
            )
        except Exception:
            pass

    def trailing_stop_enabled(
        self,
        operation,
    ):

        self._log(
            "🟪",
            f"Trailing Stop | Ticket={operation.ticket}",
        )

        try:
            event_bus.notify(
                f"Trailing Stop activado ({operation.ticket})"
            )
        except Exception:
            pass

    def partial_close(
        self,
        operation,
        volume,
    ):

        self._log(
            "🟨",
            (
                f"Cierre parcial | "
                f"Ticket={operation.ticket} | "
                f"Volumen={volume}"
            ),
        )

        try:
            event_bus.notify(
                f"Cierre parcial ({operation.ticket})"
            )
        except Exception:
            pass


operation_events = OperationEvents()
