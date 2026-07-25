from dataclasses import fields

from models.mt5_account import MT5Account
from database.database_manager import database_manager


_ACCOUNT_FIELDS = {item.name for item in fields(MT5Account)}


def _account_from_row(row):
    return MT5Account(**{
        key: value for key, value in dict(row).items()
        if key in _ACCOUNT_FIELDS
    })


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
            _account_from_row(row)
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

        return _account_from_row(row)

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
            _account_from_row(row)
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

        self._save_terminal_link(account)

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

        self._save_terminal_link(account)

        return cursor.rowcount > 0

    def _save_terminal_link(self, account):
        columns = {
            row[1] for row in database_manager.execute(
                "PRAGMA table_info(mt5_accounts)"
            ).fetchall()
        }
        if "mt5_terminal_id" not in columns or account.id is None:
            return
        database_manager.execute(
            "UPDATE mt5_accounts SET mt5_terminal_id=? WHERE id=?",
            (account.mt5_terminal_id, account.id),
        )
        database_manager.commit()

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
