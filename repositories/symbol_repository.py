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
        catalog_id=None,
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

        symbol_id = cursor.lastrowid
        self.set_catalog_context(
            symbol_id,
            profile_id,
            catalog_id,
            symbol,
        )
        return symbol_id

    # ---------------------------------------------------------

    def set_catalog_context(
        self,
        symbol_id,
        profile_id,
        catalog_id,
        canonical_name,
    ):
        if not catalog_id or not self._context_table_exists():
            return False
        cursor = database_manager.cursor()
        cursor.execute(
            """
            INSERT INTO profile_symbol_catalog_context(
                symbol_id, profile_id, catalog_id, canonical_name
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol_id) DO UPDATE SET
                profile_id=excluded.profile_id,
                catalog_id=excluded.catalog_id,
                canonical_name=excluded.canonical_name,
                updated_at=CURRENT_TIMESTAMP
            """,
            (symbol_id, profile_id, catalog_id, canonical_name),
        )
        database_manager.commit()
        return True

    def get_catalog_context(self, symbol_id):
        if not self._context_table_exists():
            return None
        row = database_manager.execute(
            """
            SELECT profile_id, catalog_id, canonical_name
            FROM profile_symbol_catalog_context
            WHERE symbol_id=?
            """,
            (symbol_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_by_catalog_symbol(self, profile_id, catalog_id, canonical_name):
        if not self._context_table_exists():
            return self.get_by_symbol(profile_id, canonical_name)
        row = database_manager.execute(
            """
            SELECT symbols.*
            FROM symbols
            JOIN profile_symbol_catalog_context context
              ON context.symbol_id=symbols.id
            WHERE context.profile_id=?
              AND context.catalog_id=?
              AND context.canonical_name=?
            LIMIT 1
            """,
            (profile_id, catalog_id, canonical_name),
        ).fetchone()
        return Symbol(**dict(row)) if row else None

    @staticmethod
    def _context_table_exists():
        return database_manager.table_exists(
            "profile_symbol_catalog_context"
        )

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
