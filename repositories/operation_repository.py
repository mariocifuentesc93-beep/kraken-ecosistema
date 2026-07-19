from models.operation import Operation


class OperationRepository:

    def __init__(self):

        self.operations = {}

    # =====================================================
    # CRUD
    # =====================================================

    def add(
        self,
        operation: Operation,
    ):

        self.operations[operation.operation_id] = operation

        return operation

    def get(
        self,
        operation_id,
    ):

        return self.operations.get(operation_id)

    def update(
        self,
        operation: Operation,
    ):

        self.operations[operation.operation_id] = operation

        return operation

    def remove(
        self,
        operation_id,
    ):

        return self.operations.pop(operation_id, None)

    def clear(self):

        self.operations.clear()

    def exists(
        self,
        operation_id,
    ):

        return operation_id in self.operations

    # =====================================================
    # LISTS
    # =====================================================

    def get_all(self):

        return sorted(
            self.operations.values(),
            key=lambda x: getattr(x, "created_at", None),
            reverse=True,
        )

    def get_pending(self):

        return [
            op
            for op in self.operations.values()
            if getattr(op, "status", "") == "PENDING"
        ]

    def get_created(self):

        return [
            op
            for op in self.operations.values()
            if getattr(op, "status", "") == "CREATED"
        ]

    def get_open(self):

        return [
            op
            for op in self.operations.values()
            if getattr(op, "status", "") == "OPEN"
        ]

    def get_closed(self):

        return [
            op
            for op in self.operations.values()
            if getattr(op, "status", "") == "CLOSED"
        ]

    # =====================================================
    # SEARCH
    # =====================================================

    def get_by_ticket(
        self,
        ticket,
    ):

        for op in self.operations.values():

            if getattr(op, "ticket", None) == ticket:

                return op

        return None

    def get_by_profile(
        self,
        profile_id,
    ):

        return [
            op
            for op in self.operations.values()
            if getattr(op, "profile_id", None) == profile_id
        ]

    def get_by_account(
        self,
        account_id,
    ):

        return [
            op
            for op in self.operations.values()
            if getattr(op, "mt5_account_id", None) == account_id
        ]

    def get_by_symbol(
        self,
        symbol,
    ):

        return [
            op
            for op in self.operations.values()
            if getattr(op, "symbol", None) == symbol
        ]

    def get_by_magic(
        self,
        magic,
    ):

        return [
            op
            for op in self.operations.values()
            if getattr(op, "magic", None) == magic
        ]

    # =====================================================
    # COUNTERS
    # =====================================================

    def count(self):

        return len(self.operations)

    def count_open(self):

        return len(self.get_open())

    def count_closed(self):

        return len(self.get_closed())

    def count_pending(self):

        return len(self.get_pending())

    # =====================================================
    # RESULTS
    # =====================================================

    def get_wins(self):

        return [
            op
            for op in self.get_closed()
            if getattr(op, "profit", 0) > 0
        ]

    def get_losses(self):

        return [
            op
            for op in self.get_closed()
            if getattr(op, "profit", 0) < 0
        ]

    def get_breakeven(self):

        return [
            op
            for op in self.get_closed()
            if getattr(op, "profit", 0) == 0
        ]

    def win_rate(self):

        closed = self.get_closed()

        if not closed:
            return 0.0

        return round(
            (len(self.get_wins()) / len(closed)) * 100,
            2,
        )

    # =====================================================
    # PROFIT
    # =====================================================

    def total_profit(self):

        return round(
            sum(
                getattr(op, "profit", 0)
                for op in self.get_closed()
            ),
            2,
        )

    def total_profit_by_profile(
        self,
        profile_id,
    ):

        return round(
            sum(
                getattr(op, "profit", 0)
                for op in self.get_closed()
                if getattr(op, "profile_id", None) == profile_id
            ),
            2,
        )

    def total_profit_by_account(
        self,
        account_id,
    ):

        return round(
            sum(
                getattr(op, "profit", 0)
                for op in self.get_closed()
                if getattr(op, "mt5_account_id", None) == account_id
            ),
            2,
        )


operation_repository = OperationRepository()