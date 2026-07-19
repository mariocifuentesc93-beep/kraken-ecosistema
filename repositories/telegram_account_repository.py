from models.telegram_account import TelegramAccount
from database.database_manager import database_manager


class TelegramAccountRepository:

    # ---------------------------------------------------------

    def get_all(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM telegram_accounts

            ORDER BY name
            """
        )

        return [
            TelegramAccount(**dict(row))
            for row in cursor.fetchall()
        ]

    # ---------------------------------------------------------

    def get_enabled(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM telegram_accounts

            WHERE enabled=1

            ORDER BY
                auto_connect DESC,
                name
            """
        )

        return [
            TelegramAccount(**dict(row))
            for row in cursor.fetchall()
        ]

    # ---------------------------------------------------------

    def get_by_id(self, account_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM telegram_accounts

            WHERE id=?

            LIMIT 1
            """,
            (account_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return TelegramAccount(**dict(row))

    # ---------------------------------------------------------

    def get_auto_connect(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM telegram_accounts

            WHERE
                enabled=1
                AND auto_connect=1

            LIMIT 1
            """
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return TelegramAccount(**dict(row))

    # ---------------------------------------------------------

    def create(self, account: TelegramAccount):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            INSERT INTO telegram_accounts
            (
                name,
                phone,
                api_id,
                api_hash,
                session_name,

                enabled,
                auto_connect,
                connected,
                authorized,

                last_error,

                user_id,
                username,
                first_name,
                last_name,

                created_at,
                updated_at
            )

            VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                account.name,
                account.phone,
                account.api_id,
                account.api_hash,
                account.session_name,

                int(account.enabled),
                int(account.auto_connect),
                int(account.connected),
                int(account.authorized),

                account.last_error,

                account.user_id,
                account.username,
                account.first_name,
                account.last_name,

                account.created_at,
                account.updated_at,
            ),
        )

        database_manager.commit()

        account.id = cursor.lastrowid

        return account

    # ---------------------------------------------------------

    def update(self, account: TelegramAccount):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            UPDATE telegram_accounts

            SET

                name=?,
                phone=?,
                api_id=?,
                api_hash=?,
                session_name=?,

                enabled=?,
                auto_connect=?,
                connected=?,
                authorized=?,

                last_error=?,

                user_id=?,
                username=?,
                first_name=?,
                last_name=?,

                updated_at=?

            WHERE id=?
            """,
            (
                account.name,
                account.phone,
                account.api_id,
                account.api_hash,
                account.session_name,

                int(account.enabled),
                int(account.auto_connect),
                int(account.connected),
                int(account.authorized),

                account.last_error,

                account.user_id,
                account.username,
                account.first_name,
                account.last_name,

                account.updated_at,

                account.id,
            ),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # ---------------------------------------------------------

    def delete(self, account_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            DELETE FROM telegram_accounts

            WHERE id=?
            """,
            (account_id,),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # ---------------------------------------------------------

    def exists(self, account_id):

        return self.get_by_id(account_id) is not None

    # ---------------------------------------------------------

    def count(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM telegram_accounts
            """
        )

        return cursor.fetchone()[0]


telegram_account_repository = TelegramAccountRepository()