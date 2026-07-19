from datetime import datetime


class SimulationEngine:

    def __init__(self):
        self.operations = []

    def execute(self, signal):
        operation = {
            "ticket": len(self.operations) + 1,
            "symbol": signal.get("symbol"),
            "direction": signal.get("direction"),
            "entry": signal.get("entry"),
            "stop_loss": signal.get("stop_loss"),
            "take_profits": signal.get("take_profits", []),
            "status": "OPEN",
            "opened_at": datetime.now(),
        }

        self.operations.append(operation)

        print(
            f"[SIMULATION] Operación simulada #{operation['ticket']} "
            f"{operation['direction']} {operation['symbol']}"
        )

        return operation

    def get_open_operations(self):
        return [
            op for op in self.operations
            if op["status"] == "OPEN"
        ]

    def close_operation(self, ticket):

        for operation in self.operations:

            if operation["ticket"] == ticket:

                operation["status"] = "CLOSED"
                operation["closed_at"] = datetime.now()

                return True

        return False

    def get_statistics(self):

        total = len(self.operations)

        open_ops = len(
            [
                op for op in self.operations
                if op["status"] == "OPEN"
            ]
        )

        closed = total - open_ops

        return {
            "total": total,
            "open": open_ops,
            "closed": closed,
        }


simulation_engine = SimulationEngine()