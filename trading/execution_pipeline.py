from datetime import datetime

from models.operation import Operation
from repositories.execution_timeline_repository import execution_timeline_repository
from repositories.market_price_event_repository import market_price_event_repository
from repositories.operation_repository import operation_repository
from services.market_data_service import market_data_service


STATE_ORDER = ("NEW", "PARSED", "VALIDATED", "RISK_APPROVED", "QUEUED", "SIMULATED", "EXECUTED", "TP1", "TP2", "TP3", "CLOSED")
TERMINAL_STATES = {"REJECTED", "CANCELLED", "ERROR", "EXPIRED", "CLOSED"}


class ExecutionPipeline:
    def create(self, signal, profile, account=None, execution_mode="SIMULATION"):
        operation = Operation(signal=signal, profile=profile, account=account, status="NEW")
        operation.opened_at = datetime.now()
        operation_repository.create(operation)
        self.transition(operation, "NEW", "Se creó la operación", execution_mode)
        return operation

    def transition(self, operation, state, reason="", execution_mode="SIMULATION"):
        previous = operation.status
        operation.status = state
        operation.updated_at = datetime.now()
        if state in TERMINAL_STATES:
            operation.closed_at = operation.updated_at
        operation_repository.update(operation)
        execution_timeline_repository.record(operation, previous, state, reason, execution_mode)
        return operation

    def simulate(self, signal, profile, account=None, outcome="tp3"):
        operation = self.create(signal, profile, account, "SIMULATION")
        for state in ("PARSED", "VALIDATED", "RISK_APPROVED", "QUEUED"):
            self.transition(operation, state, "Validación simulada", "SIMULATION")
        if outcome == "pending":
            return operation
        if outcome == "cancel":
            return self.transition(operation, "CANCELLED", "Orden pendiente cancelada", "SIMULATION")
        if outcome == "expired":
            return self.transition(operation, "EXPIRED", "Orden pendiente expirada", "SIMULATION")
        if outcome == "error":
            return self.transition(operation, "ERROR", "Error simulado", "SIMULATION")
        self.transition(operation, "SIMULATED", "Ejecución de mercado simulada", "SIMULATION")
        if outcome == "sl":
            operation.result = "SL"
            return self.transition(operation, "CLOSED", "Stop Loss simulado", "SIMULATION")
        self.transition(operation, "TP1", "TP1 alcanzado", "SIMULATION")
        if outcome == "tp1":
            return self.transition(operation, "CLOSED", "Cierre TP1", "SIMULATION")
        self.transition(operation, "TP2", "TP2 alcanzado", "SIMULATION")
        if outcome == "tp2":
            return self.transition(operation, "CLOSED", "Cierre TP2", "SIMULATION")
        self.transition(operation, "TP3", "TP3 alcanzado", "SIMULATION")
        operation.result = "TP3"
        return self.transition(operation, "CLOSED", "Cierre TP3", "SIMULATION")

    def simulate_with_market_data(self, signal, profile, account=None, quote=None,
                                  freshness_seconds=None):
        """Advance a simulation using a read-only MT5 or fallback quote.

        LIVE execution is intentionally not represented here: every transition
        is written as SIMULATION regardless of a caller's profile setting.
        """
        operation = self.create(signal, profile, account, "SIMULATION")
        for state in ("PARSED", "VALIDATED", "RISK_APPROVED", "QUEUED"):
            self.transition(operation, state, "Validación de simulación", "SIMULATION")
        quote = quote or market_data_service.quote(signal.symbol, freshness_seconds)
        market_price_event_repository.record(operation, quote, "QUOTE_RECEIVED")
        received_at = getattr(signal, "received_at", None)
        if received_at and (datetime.now() - received_at.replace(tzinfo=None)).total_seconds() > 300:
            return self.transition(operation, "EXPIRED", "Señal expirada", "SIMULATION")
        if not quote.get("available"):
            return self.transition(operation, "REJECTED", quote.get("stale_reason", "Precio no disponible"), "SIMULATION")
        if not quote.get("fresh"):
            return self.transition(operation, "REJECTED", quote.get("stale_reason", "Tick vencido"), "SIMULATION")
        if not quote.get("market_open"):
            return self.transition(operation, "EXPIRED", "Mercado cerrado", "SIMULATION")

        entry = float(getattr(signal, "entry", 0) or 0)
        is_buy = str(getattr(signal, "direction", "")).upper() == "BUY"
        fill_price = quote["ask"] if is_buy else quote["bid"]
        pending = bool(entry) and not getattr(signal, "market_execution", False)
        if pending and not self._pending_is_activated(is_buy, entry, fill_price):
            market_price_event_repository.record(operation, quote, "PENDING_WAIT")
            return operation

        operation.entry_price = fill_price
        self.transition(operation, "SIMULATED", "Entrada simulada con precio de mercado", "SIMULATION")
        market_price_event_repository.record(operation, quote, "ENTRY_FILLED")
        return self.evaluate_market_price(operation, signal, quote)

    @staticmethod
    def _pending_is_activated(is_buy, entry, price):
        # A buy limit activates at/below entry and a sell limit at/above entry.
        return price <= entry if is_buy else price >= entry

    def evaluate_market_price(self, operation, signal, quote):
        """Apply one quote to an active simulation for SL/TP detection."""
        if operation.status not in {"SIMULATED", "TP1", "TP2"}:
            return operation
        is_buy = str(getattr(signal, "direction", "")).upper() == "BUY"
        price = quote["bid"] if is_buy else quote["ask"]
        market_price_event_repository.record(operation, quote, "PRICE_EVALUATED")
        stop_loss = float(getattr(signal, "stop_loss", 0) or 0)
        if stop_loss and ((is_buy and price <= stop_loss) or (not is_buy and price >= stop_loss)):
            operation.result = "SL"
            return self.transition(operation, "CLOSED", "Stop Loss detectado", "SIMULATION")

        targets = list(getattr(signal, "take_profits", []) or [])
        hit = lambda target: price >= target if is_buy else price <= target
        for index, target in enumerate(targets[:3], 1):
            state = f"TP{index}"
            if hit(float(target)) and operation.status not in {state, "TP3"}:
                self.transition(operation, state, f"{state} detectado", "SIMULATION")
                if index == len(targets[:3]) or index == 3:
                    operation.result = state
                    return self.transition(operation, "CLOSED", f"Cierre {state}", "SIMULATION")
        return operation


execution_pipeline = ExecutionPipeline()
