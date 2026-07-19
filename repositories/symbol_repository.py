from models.symbol import Symbol
from database.database_manager import database_manager


class SymbolRepository:

    # ---------------------------------------------------------

    def get_all(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM symbols

            WHERE profile_id=?

            ORDER BY symbol
            """,
            (profile_id,),
        )

        return [

            Symbol(**dict(row))

            for row in cursor.fetchall()

        ]

    # ---------------------------------------------------------

    def get_enabled(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM symbols

            WHERE
                profile_id=?
                AND enabled=1

            ORDER BY symbol
            """,
            (profile_id,),
        )

        return [

            Symbol(**dict(row))

            for row in cursor.fetchall()

        ]

    # ---------------------------------------------------------

    def get_by_id(self, symbol_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM symbols

            WHERE id=?

            LIMIT 1
            """,
            (symbol_id,),
        )

        row = cursor.fetchone()

        if row is None:

            return None

        return Symbol(**dict(row))

    # ---------------------------------------------------------

    def get_by_symbol(self, profile_id, symbol):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM symbols

            WHERE
                profile_id=?
                AND UPPER(symbol)=UPPER(?)

            LIMIT 1
            """,
            (
                profile_id,
                symbol,
            ),
        )

        row = cursor.fetchone()

        if row is None:

            return None

        return Symbol(**dict(row))

    # ---------------------------------------------------------

    def create(
        self,
        profile_id,
        enabled,
        symbol,
        mt5_symbol,
        description,
        aliases,
        risk,
        min_lot,
        max_lot,
        action,
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            INSERT INTO symbols
            (
                profile_id,
                enabled,
                symbol,
                mt5_symbol,
                description,
                aliases,
                risk,
                min_lot,
                max_lot,
                action
            )

            VALUES
            (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                profile_id,
                int(enabled),
                symbol,
                mt5_symbol,
                description,
                aliases,
                risk,
                min_lot,
                max_lot,
                action,
            ),
        )

        database_manager.commit()

        return cursor.lastrowid

    # ---------------------------------------------------------

    def update(
        self,
        symbol_id,
        enabled,
        mt5_symbol,
        description,
        aliases,
        risk,
        min_lot,
        max_lot,
        action,
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            UPDATE symbols

            SET

                enabled=?,
                mt5_symbol=?,
                description=?,
                aliases=?,
                risk=?,
                min_lot=?,
                max_lot=?,
                action=?

            WHERE id=?
            """,
            (
                int(enabled),
                mt5_symbol,
                description,
                aliases,
                risk,
                min_lot,
                max_lot,
                action,
                symbol_id,
            ),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # ---------------------------------------------------------

    def delete(self, symbol_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            DELETE FROM symbols

            WHERE id=?
            """,
            (symbol_id,),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # ---------------------------------------------------------

    def exists(self, profile_id, symbol):

        return self.get_by_symbol(
            profile_id,
            symbol,
        ) is not None

    # ---------------------------------------------------------

    def count(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM symbols

            WHERE profile_id=?
            """,
            (profile_id,),
        )

        return cursor.fetchone()[0]


symbol_repository = SymbolRepository()