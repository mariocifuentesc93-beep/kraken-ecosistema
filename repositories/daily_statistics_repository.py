from datetime import datetime

from database.database_manager import database_manager


class DailyStatisticsRepository:

    # =====================================================
    # CREATE / UPDATE
    # =====================================================

    def save(
        self,
        profile_id,
        statistic_date,
        operations,
        wins,
        losses,
        breakeven,
        gross_profit,
        gross_loss,
        net_profit,
        win_rate,
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT id

            FROM daily_statistics

            WHERE
                profile_id=?
                AND statistic_date=?
            """,
            (
                profile_id,
                statistic_date,
            ),
        )

        row = cursor.fetchone()

        if row:

            cursor.execute(
                """
                UPDATE daily_statistics

                SET

                    operations=?,
                    wins=?,
                    losses=?,
                    breakeven=?,
                    gross_profit=?,
                    gross_loss=?,
                    net_profit=?,
                    win_rate=?

                WHERE id=?
                """,
                (
                    operations,
                    wins,
                    losses,
                    breakeven,
                    gross_profit,
                    gross_loss,
                    net_profit,
                    win_rate,
                    row["id"],
                ),
            )

        else:

            cursor.execute(
                """
                INSERT INTO daily_statistics
                (
                    profile_id,
                    statistic_date,
                    operations,
                    wins,
                    losses,
                    breakeven,
                    gross_profit,
                    gross_loss,
                    net_profit,
                    win_rate
                )

                VALUES
                (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    profile_id,
                    statistic_date,
                    operations,
                    wins,
                    losses,
                    breakeven,
                    gross_profit,
                    gross_loss,
                    net_profit,
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

            FROM daily_statistics

            WHERE profile_id=?

            ORDER BY statistic_date DESC
            """,
            (profile_id,),
        )

        return cursor.fetchall()

    # =====================================================

    def get_by_date(self, profile_id, statistic_date):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM daily_statistics

            WHERE
                profile_id=?
                AND statistic_date=?
            """,
            (
                profile_id,
                statistic_date,
            ),
        )

        return cursor.fetchone()

    # =====================================================

    def get_last(self, profile_id, limit=30):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM daily_statistics

            WHERE profile_id=?

            ORDER BY statistic_date DESC

            LIMIT ?
            """,
            (
                profile_id,
                limit,
            ),
        )

        return cursor.fetchall()

    # =====================================================

    def get_month(self, profile_id, year, month):

        prefix = f"{year:04d}-{month:02d}"

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM daily_statistics

            WHERE
                profile_id=?
                AND statistic_date LIKE ?

            ORDER BY statistic_date
            """,
            (
                profile_id,
                prefix + "%",
            ),
        )

        return cursor.fetchall()

    # =====================================================

    def delete(self, statistic_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            DELETE FROM daily_statistics

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
            DELETE FROM daily_statistics
            """
        )

        database_manager.commit()

    # =====================================================

    def count(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM daily_statistics
            """
        )

        return cursor.fetchone()[0]

    # =====================================================

    def today(self, profile_id):

        return self.get_by_date(
            profile_id,
            datetime.now().strftime("%Y-%m-%d"),
        )


daily_statistics_repository = DailyStatisticsRepository()