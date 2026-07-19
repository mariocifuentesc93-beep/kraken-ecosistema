from datetime import datetime

from database.database_manager import database_manager


class OperationEventsRepository:

    # =====================================================
    # CREATE
    # =====================================================

    def create(
        self,
        operation_id,
        event,
        description="",
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            INSERT INTO operation_events
            (
                operation_id,
                event,
                description,
                created_at
            )
            VALUES
            (?,?,?,?)
            """,
            (
                operation_id,
                event,
                description,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            ),
        )

        database_manager.commit()

        return cursor.lastrowid

    # =====================================================
    # CONSULTAS
    # =====================================================

    def get_all(self, operation_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM operation_events

            WHERE operation_id=?

            ORDER BY id
            """,
            (operation_id,),
        )

        return cursor.fetchall()

    # =====================================================

    def get_last(self, limit=200):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM operation_events

            ORDER BY id DESC

            LIMIT ?
            """,
            (limit,),
        )

        return cursor.fetchall()

    # =====================================================

    def get_by_event(
        self,
        operation_id,
        event,
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM operation_events

            WHERE
                operation_id=?
                AND event=?

            ORDER BY id
            """,
            (
                operation_id,
                event,
            ),
        )

        return cursor.fetchall()

    # =====================================================

    def exists(
        self,
        operation_id,
        event,
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM operation_events

            WHERE
                operation_id=?
                AND event=?
            """,
            (
                operation_id,
                event,
            ),
        )

        return cursor.fetchone()[0] > 0

    # =====================================================

    def delete(self, event_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            DELETE FROM operation_events

            WHERE id=?
            """,
            (event_id,),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # =====================================================

    def clear(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            DELETE FROM operation_events
            """
        )

        database_manager.commit()

    # =====================================================

    def count(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM operation_events
            """
        )

        return cursor.fetchone()[0]


operation_events_repository = OperationEventsRepository()