from datetime import datetime

from database.database_manager import database_manager
from models.signal import Signal


class SignalRepository:

    # =====================================================
    # CREATE
    # =====================================================

    def create(self, signal: Signal):

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not signal.created_at:
            signal.created_at = now

        cursor = database_manager.cursor()

        cursor.execute(
            """
            INSERT INTO signals
            (
                telegram_account_id,
                profile_id,
                symbol,
                direction,
                entry,
                stop_loss,
                tp1,
                tp2,
                tp3,
                market_execution,
                raw_message,
                status,
                created_at
            )
            VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                signal.telegram_account_id,
                signal.profile_id,
                signal.symbol,
                signal.direction,
                signal.entry,
                signal.stop_loss,
                signal.tp1,
                signal.tp2,
                signal.tp3,
                int(signal.market_execution),
                signal.raw_message,
                signal.status,
                signal.created_at,
            ),
        )

        database_manager.commit()

        signal.id = cursor.lastrowid

        return signal

    # =====================================================
    # READ
    # =====================================================

    def get_by_id(self, signal_id):

        cursor = database_manager.cursor()

        cursor.execute(
            "SELECT * FROM signals WHERE id=?",
            (signal_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return Signal(**dict(row))

    # =====================================================

    def get_all(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM signals

            ORDER BY id DESC
            """
        )

        return [

            Signal(**dict(row))

            for row in cursor.fetchall()

        ]

    # =====================================================

    def get_last(self, limit=100):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM signals

            ORDER BY id DESC

            LIMIT ?
            """,
            (limit,),
        )

        return [

            Signal(**dict(row))

            for row in cursor.fetchall()

        ]

    # =====================================================

    def get_by_profile(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM signals

            WHERE profile_id=?

            ORDER BY id DESC
            """,
            (profile_id,),
        )

        return [

            Signal(**dict(row))

            for row in cursor.fetchall()

        ]

    # =====================================================

    def get_by_status(self, status):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM signals

            WHERE status=?

            ORDER BY id DESC
            """,
            (status,),
        )

        return [

            Signal(**dict(row))

            for row in cursor.fetchall()

        ]

    # =====================================================

    def get_by_telegram_account(self, telegram_account_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM signals

            WHERE telegram_account_id=?

            ORDER BY id DESC
            """,
            (telegram_account_id,),
        )

        return [

            Signal(**dict(row))

            for row in cursor.fetchall()

        ]

    # =====================================================
    # UPDATE
    # =====================================================

    def update_status(self, signal_id, status):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            UPDATE signals

            SET status=?

            WHERE id=?
            """,
            (
                status,
                signal_id,
            ),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # =====================================================

    def update_profile(self, signal_id, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            UPDATE signals

            SET profile_id=?

            WHERE id=?
            """,
            (
                profile_id,
                signal_id,
            ),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # =====================================================

    def update_prices(
        self,
        signal_id,
        entry,
        stop_loss,
        tp1,
        tp2,
        tp3,
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            UPDATE signals

            SET

                entry=?,
                stop_loss=?,
                tp1=?,
                tp2=?,
                tp3=?

            WHERE id=?
            """,
            (
                entry,
                stop_loss,
                tp1,
                tp2,
                tp3,
                signal_id,
            ),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # =====================================================
    # DELETE
    # =====================================================

    def delete(self, signal_id):

        cursor = database_manager.cursor()

        cursor.execute(
            "DELETE FROM signals WHERE id=?",
            (signal_id,),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # =====================================================
    # HELPERS
    # =====================================================

    def count(self):

        cursor = database_manager.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM signals"
        )

        return cursor.fetchone()[0]

    # =====================================================

    def clear(self):

        cursor = database_manager.cursor()

        cursor.execute(
            "DELETE FROM signals"
        )

        database_manager.commit()


signal_repository = SignalRepository()
