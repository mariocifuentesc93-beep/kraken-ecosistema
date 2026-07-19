from database.database_manager import database_manager


class SymbolStatisticsRepository:

    # =====================================================
    # CREATE / UPDATE
    # =====================================================

    def save(
        self,
        profile_id,
        symbol,
        operations,
        wins,
        losses,
        breakeven,
        profit,
        loss,
        win_rate,
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT id

            FROM symbol_statistics

            WHERE
                profile_id=?
                AND symbol=?
            """,
            (
                profile_id,
                symbol,
            ),
        )

        row = cursor.fetchone()

        if row:

            cursor.execute(
                """
                UPDATE symbol_statistics

                SET

                    operations=?,
                    wins=?,
                    losses=?,
                    breakeven=?,
                    profit=?,
                    loss=?,
                    win_rate=?

                WHERE id=?
                """,
                (
                    operations,
                    wins,
                    losses,
                    breakeven,
                    profit,
                    loss,
                    win_rate,
                    row["id"],
                ),
            )

        else:

            cursor.execute(
                """
                INSERT INTO symbol_statistics
                (
                    profile_id,
                    symbol,
                    operations,
                    wins,
                    losses,
                    breakeven,
                    profit,
                    loss,
                    win_rate
                )

                VALUES
                (?,?,?,?,?,?,?,?,?)
                """,
                (
                    profile_id,
                    symbol,
                    operations,
                    wins,
                    losses,
                    breakeven,
                    profit,
                    loss,
                    win_rate,
                ),
            )

        database_manager.commit()

    # =====================================================
    # CONSULTAS
    # =====================================================

    def get_all(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM symbol_statistics

            WHERE profile_id=?

            ORDER BY symbol
            """,
            (profile_id,),
        )

        return cursor.fetchall()

    # =====================================================

    def get_symbol(self, profile_id, symbol):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM symbol_statistics

            WHERE
                profile_id=?
                AND symbol=?
            """,
            (
                profile_id,
                symbol,
            ),
        )

        return cursor.fetchone()

    # =====================================================

    def get_best(self, profile_id, limit=10):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM symbol_statistics

            WHERE profile_id=?

            ORDER BY
                win_rate DESC,
                operations DESC

            LIMIT ?
            """,
            (
                profile_id,
                limit,
            ),
        )

        return cursor.fetchall()

    # =====================================================

    def get_worst(self, profile_id, limit=10):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM symbol_statistics

            WHERE profile_id=?

            ORDER BY
                win_rate ASC,
                operations DESC

            LIMIT ?
            """,
            (
                profile_id,
                limit,
            ),
        )

        return cursor.fetchall()

    # =====================================================

    def delete(self, statistic_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            DELETE FROM symbol_statistics

            WHERE id=?
            """,
            (statistic_id,),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # =====================================================

    def clear(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            DELETE FROM symbol_statistics
            """
        )

        database_manager.commit()

    # =====================================================

    def count(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM symbol_statistics
            """
        )

        return cursor.fetchone()[0]


symbol_statistics_repository = SymbolStatisticsRepository()