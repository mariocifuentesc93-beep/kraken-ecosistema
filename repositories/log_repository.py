from datetime import datetime

from database.database_manager import database_manager


class LogRepository:

    # =====================================================
    # CREATE
    # =====================================================

    def add(self, level, module, message):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            INSERT INTO logs
            (
                level,
                module,
                message,
                created_at
            )
            VALUES
            (?,?,?,?)
            """,
            (
                level,
                module,
                message,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

        database_manager.commit()

        return cursor.lastrowid

    # =====================================================

    def info(self, module, message):

        return self.add(
            "INFO",
            module,
            message,
        )

    # =====================================================

    def warning(self, module, message):

        return self.add(
            "WARNING",
            module,
            message,
        )

    # =====================================================

    def error(self, module, message):

        return self.add(
            "ERROR",
            module,
            message,
        )

    # =====================================================

    def debug(self, module, message):

        return self.add(
            "DEBUG",
            module,
            message,
        )

    # =====================================================
    # CONSULTAS
    # =====================================================

    def get_all(self, limit=500):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM logs

            ORDER BY id DESC

            LIMIT ?
            """,
            (limit,),
        )

        return cursor.fetchall()

    # =====================================================

    def get_by_level(self, level, limit=500):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM logs

            WHERE level=?

            ORDER BY id DESC

            LIMIT ?
            """,
            (
                level,
                limit,
            ),
        )

        return cursor.fetchall()

    # =====================================================

    def get_by_module(self, module, limit=500):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM logs

            WHERE module=?

            ORDER BY id DESC

            LIMIT ?
            """,
            (
                module,
                limit,
            ),
        )

        return cursor.fetchall()

    # =====================================================

    def search(self, text, limit=500):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM logs

            WHERE message LIKE ?

            ORDER BY id DESC

            LIMIT ?
            """,
            (
                f"%{text}%",
                limit,
            ),
        )

        return cursor.fetchall()

    # =====================================================

    def count(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM logs
            """
        )

        return cursor.fetchone()[0]

    # =====================================================

    def clear(self):

        cursor = database_manager.cursor()

        cursor.execute(
            "DELETE FROM logs"
        )

        database_manager.commit()

    # =====================================================

    def delete_older_than(self, date_string):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            DELETE FROM logs

            WHERE created_at < ?
            """,
            (date_string,),
        )

        database_manager.commit()

        return cursor.rowcount


log_repository = LogRepository()