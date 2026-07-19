from models.mt5_account import MT5Account
from database.database_manager import database_manager


class MT5AccountRepository:

    # ---------------------------------------------------------

    def get_all(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *
            FROM mt5_accounts
            ORDER BY name
            """
        )

        return [
            MT5Account(**dict(row))
            for row in cursor.fetchall()
        ]

    # ---------------------------------------------------------

    def get_by_id(self, account_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *
            FROM mt5_accounts
            WHERE id=?
            """,
            (account_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return MT5Account(**dict(row))

    # ---------------------------------------------------------

    def get_enabled(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *
            FROM mt5_accounts
            WHERE active=1
            ORDER BY name
            """
        )

        return [
            MT5Account(**dict(row))
            for row in cursor.fetchall()
        ]

    # ---------------------------------------------------------

    def create(self, account: MT5Account):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            INSERT INTO mt5_accounts
            (
                name,
                login,
                password,
                server,
                terminal_path,

                execution_mode,

                risk_enabled,
                risk_mode,
                risk_percent,
                risk_amount,
                fixed_lot,

                magic_number,
                custom_magic,
                comment,
                deviation,

                active,
                auto_connect,
                reconnect,

                description
            )

            VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                account.name,
                account.login,
                account.password,
                account.server,
                account.terminal_path,

                account.execution_mode,

                int(bool(account.risk_enabled)),
                account.risk_mode,
                account.risk_percent,
                account.risk_amount,
                account.fixed_lot,

                account.magic_number,
                account.custom_magic,
                account.comment,
                account.deviation,

                int(bool(account.active)),
                int(bool(account.auto_connect)),
                int(bool(account.reconnect)),

                account.description,
            ),
        )

        database_manager.commit()

        account.id = cursor.lastrowid

        return account

    # ---------------------------------------------------------

    def update(self, account: MT5Account):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            UPDATE mt5_accounts
            SET

                name=?,
                login=?,
                password=?,
                server=?,
                terminal_path=?,

                execution_mode=?,

                risk_enabled=?,
                risk_mode=?,
                risk_percent=?,
                risk_amount=?,
                fixed_lot=?,

                magic_number=?,
                custom_magic=?,
                comment=?,
                deviation=?,

                active=?,
                auto_connect=?,
                reconnect=?,

                description=?

            WHERE id=?
            """,
            (
                account.name,
                account.login,
                account.password,
                account.server,
                account.terminal_path,

                account.execution_mode,

                int(bool(account.risk_enabled)),
                account.risk_mode,
                account.risk_percent,
                account.risk_amount,
                account.fixed_lot,

                account.magic_number,
                account.custom_magic,
                account.comment,
                account.deviation,

                int(bool(account.active)),
                int(bool(account.auto_connect)),
                int(bool(account.reconnect)),

                account.description,

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
            DELETE FROM mt5_accounts
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
            FROM mt5_accounts
            """
        )

        return cursor.fetchone()[0]


mt5_account_repository = MT5AccountRepository()