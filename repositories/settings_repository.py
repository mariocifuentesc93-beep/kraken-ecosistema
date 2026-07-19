from database.database_manager import database_manager


class SettingsRepository:

    # =====================================================
    # GET
    # =====================================================

    def get(self, key, default=None):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT value

            FROM settings

            WHERE key=?

            LIMIT 1
            """,
            (key,),
        )

        row = cursor.fetchone()

        if row is None:

            return default

        return row["value"]

    # =====================================================

    def get_bool(self, key, default=False):

        value = self.get(key)

        if value is None:

            return default

        return str(value).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    # =====================================================

    def get_int(self, key, default=0):

        value = self.get(key)

        try:

            return int(value)

        except Exception:

            return default

    # =====================================================

    def get_float(self, key, default=0.0):

        value = self.get(key)

        try:

            return float(value)

        except Exception:

            return default

    # =====================================================
    # SET
    # =====================================================

    def set(self, key, value):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            INSERT INTO settings
            (
                key,
                value
            )
            VALUES
            (?,?)
            ON CONFLICT(key)
            DO UPDATE SET
                value=excluded.value
            """,
            (
                key,
                str(value),
            ),
        )

        database_manager.commit()

    # =====================================================

    def remove(self, key):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            DELETE FROM settings

            WHERE key=?
            """,
            (key,),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # =====================================================

    def exists(self, key):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM settings

            WHERE key=?
            """,
            (key,),
        )

        return cursor.fetchone()[0] > 0

    # =====================================================

    def get_all(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM settings

            ORDER BY key
            """
        )

        return {

            row["key"]: row["value"]

            for row in cursor.fetchall()

        }

    # =====================================================

    def clear(self):

        cursor = database_manager.cursor()

        cursor.execute(
            "DELETE FROM settings"
        )

        database_manager.commit()


settings_repository = SettingsRepository()