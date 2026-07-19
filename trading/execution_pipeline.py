from datetime import datetime

from models.operation import Operation
from repositories.execution_timeline_repository import execution_timeline_repository
from repositories.operation_repository import operation_repository


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


execution_pipeline = ExecutionPipeline()
