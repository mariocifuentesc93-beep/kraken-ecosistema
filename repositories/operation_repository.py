from datetime import datetime

from database.database_manager import database_manager
from models.operation import Operation


class OperationRepository:
    """SQLite-backed operation storage with the legacy public API."""

    def create(self, operation: Operation):
        cursor = database_manager.cursor()
        cursor.execute(
            """
            INSERT INTO operations (
                signal_id, profile_id, mt5_account_id,
                ticket, magic, symbol, direction, volume, entry_price,
                exit_price, stop_loss, take_profit, profit, result, status,
                rr, partial_closed, break_even, trailing_stop,
                opened_at, closed_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            self._values(operation),
        )
        database_manager.commit()
        operation.id = cursor.lastrowid
        return operation

    def add(self, operation: Operation):
        return self.update(operation) if operation.id else self.create(operation)

    def get(self, operation_id):
        cursor = database_manager.cursor()
        cursor.execute(
            """
            SELECT * FROM operations
            WHERE id=?
            LIMIT 1
            """,
            (int(operation_id),),
        )
        row = cursor.fetchone()
        return self._to_operation(row) if row else None

    def update(self, operation: Operation):
        if not operation.id:
            return self.create(operation)

        cursor = database_manager.cursor()
        cursor.execute(
            """
            UPDATE operations SET
                signal_id=?, profile_id=?, mt5_account_id=?, ticket=?, magic=?,
                symbol=?, direction=?, volume=?,
                entry_price=?, exit_price=?, stop_loss=?, take_profit=?,
                profit=?, result=?, status=?, rr=?, partial_closed=?,
                break_even=?, trailing_stop=?, opened_at=?, closed_at=?,
                updated_at=?
            WHERE id=?
            """,
            (*self._values(operation), operation.id),
        )
        database_manager.commit()
        return operation

    def remove(self, operation_id):
        cursor = database_manager.cursor()
        cursor.execute(
            "DELETE FROM operations WHERE id=?",
            (int(operation_id),),
        )
        database_manager.commit()
        return cursor.rowcount > 0

    def clear(self):
        database_manager.execute("DELETE FROM operations")
        database_manager.commit()

    def exists(self, operation_id):
        return self.get(operation_id) is not None

    def get_all(self):
        return self._fetch("SELECT * FROM operations ORDER BY id DESC")

    def get_pending(self):
        return self._by_status("PENDING")

    def get_created(self):
        return self._by_status("CREATED")

    def get_open(self):
        return self._by_status("OPEN")

    def get_closed(self):
        return self._by_status("CLOSED")

    def get_by_ticket(self, ticket):
        matches = self._fetch(
            "SELECT * FROM operations WHERE ticket=? ORDER BY id DESC",
            (ticket,),
        )
        return matches[0] if matches else None

    def get_by_profile(self, profile_id):
        return self._fetch(
            "SELECT * FROM operations WHERE profile_id=? ORDER BY id DESC",
            (profile_id,),
        )

    def get_by_account(self, account_id):
        return self._fetch(
            "SELECT * FROM operations WHERE mt5_account_id=? ORDER BY id DESC",
            (account_id,),
        )

    def get_by_symbol(self, symbol):
        return self._fetch(
            "SELECT * FROM operations WHERE symbol=? ORDER BY id DESC",
            (symbol,),
        )

    def get_by_magic(self, magic):
        return self._fetch(
            "SELECT * FROM operations WHERE magic=? ORDER BY id DESC",
            (magic,),
        )

    def count(self):
        return self._count("SELECT COUNT(*) FROM operations")

    def count_open(self):
        return self._count("SELECT COUNT(*) FROM operations WHERE status='OPEN'")

    def count_closed(self):
        return self._count("SELECT COUNT(*) FROM operations WHERE status='CLOSED'")

    def count_pending(self):
        return self._count("SELECT COUNT(*) FROM operations WHERE status='PENDING'")

    def get_wins(self):
        return self._fetch("SELECT * FROM operations WHERE status='CLOSED' AND profit>0")

    def get_losses(self):
        return self._fetch("SELECT * FROM operations WHERE status='CLOSED' AND profit<0")

    def get_breakeven(self):
        return self._fetch("SELECT * FROM operations WHERE status='CLOSED' AND profit=0")

    def win_rate(self):
        closed = self.count_closed()
        return round(len(self.get_wins()) / closed * 100, 2) if closed else 0.0

    def total_profit(self):
        return self._total_profit()

    def total_profit_by_profile(self, profile_id):
        return self._total_profit("WHERE profile_id=?", (profile_id,))

    def total_profit_by_account(self, account_id):
        return self._total_profit("WHERE mt5_account_id=?", (account_id,))

    def _by_status(self, status):
        return self._fetch(
            "SELECT * FROM operations WHERE status=? ORDER BY id DESC",
            (status,),
        )

    def _fetch(self, sql, params=()):
        cursor = database_manager.cursor()
        cursor.execute(sql, params)
        return [self._to_operation(row) for row in cursor.fetchall()]

    def _count(self, sql):
        return database_manager.execute(sql).fetchone()[0]

    def _total_profit(self, where="", params=()):
        row = database_manager.execute(
            f"SELECT COALESCE(SUM(profit), 0) FROM operations {where}",
            params,
        ).fetchone()
        return round(float(row[0]), 2)

    @staticmethod
    def _timestamp(value):
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value

    def _values(self, operation):
        return (
            getattr(operation, "signal_id", None) or getattr(operation.signal, "id", None),
            operation.profile_id,
            operation.mt5_account_id,
            operation.ticket,
            operation.magic,
            operation.symbol,
            operation.direction,
            operation.volume,
            operation.entry_price,
            operation.exit_price,
            operation.stop_loss,
            operation.take_profit,
            operation.profit,
            operation.result,
            operation.status,
            operation.rr,
            int(bool(operation.partial_closed)),
            int(bool(operation.break_even)),
            int(bool(operation.trailing_stop)),
            self._timestamp(operation.opened_at),
            self._timestamp(operation.closed_at),
            self._timestamp(operation.updated_at or datetime.now()),
        )

    @staticmethod
    def _to_operation(row):
        return Operation(
            id=row["id"],
            profile_id=row["profile_id"],
            mt5_account_id=row["mt5_account_id"],
            ticket=row["ticket"],
            magic=row["magic"] or 0,
            symbol=row["symbol"] or "",
            direction=row["direction"] or "",
            volume=row["volume"] or 0.0,
            entry_price=row["entry_price"] or 0.0,
            exit_price=row["exit_price"] or 0.0,
            stop_loss=row["stop_loss"] or 0.0,
            take_profit=row["take_profit"] or 0.0,
            profit=row["profit"] or 0.0,
            result=row["result"] or "",
            status=row["status"] or "CREATED",
            rr=row["rr"] or 0.0,
            partial_closed=bool(row["partial_closed"]),
            break_even=bool(row["break_even"]),
            trailing_stop=bool(row["trailing_stop"]),
            opened_at=row["opened_at"],
            closed_at=row["closed_at"],
            updated_at=row["updated_at"],
        )


operation_repository = OperationRepository()
