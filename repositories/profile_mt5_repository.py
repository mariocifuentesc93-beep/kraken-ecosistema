from database.database_manager import database_manager
from models.mt5_account import MT5Account


class ProfileMT5Repository:

    # =====================================================
    # CONSULTAS
    # =====================================================

    def get_all(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT
                p.*,
                a.*
            FROM profile_mt5_accounts p
            INNER JOIN mt5_accounts a
                ON a.id = p.mt5_account_id
            WHERE p.profile_id=?
            ORDER BY p.priority, a.name
            """,
            (profile_id,),
        )

        return [dict(row) for row in cursor.fetchall()]

    # -----------------------------------------------------

    def get_accounts(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT
                a.*,

                p.id                    AS profile_mt5_id,
                p.priority,
                p.enabled,

                p.execution_mode,

                p.risk_mode,
                p.risk_percent,
                p.risk_amount,
                p.fixed_lot,

                p.custom_magic,
                p.comment

            FROM mt5_accounts a

            INNER JOIN profile_mt5_accounts p
                ON a.id = p.mt5_account_id

            WHERE
                p.profile_id=?
                AND p.enabled=1
                AND a.active=1

            ORDER BY
                p.priority,
                a.name
            """,
            (profile_id,),
        )

        return [
            MT5Account(**dict(row))
            for row in cursor.fetchall()
        ]

    # -----------------------------------------------------

    def get_account(
        self,
        profile_id,
        account_id,
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT
                a.*,

                p.id                    AS profile_mt5_id,
                p.priority,
                p.enabled,

                p.execution_mode,

                p.risk_mode,
                p.risk_percent,
                p.risk_amount,
                p.fixed_lot,

                p.custom_magic,
                p.comment

            FROM mt5_accounts a

            INNER JOIN profile_mt5_accounts p
                ON a.id=p.mt5_account_id

            WHERE
                p.profile_id=?
                AND a.id=?

            LIMIT 1
            """,
            (
                profile_id,
                account_id,
            ),
        )

        row = cursor.fetchone()

        if row is None:

            return None

        return MT5Account(**dict(row))

    # =====================================================
    # CREATE
    # =====================================================

    def create(
        self,
        profile_id,
        mt5_account_id,
        priority=1,
        enabled=True,
        execution_mode="PROFILE",
        risk_mode="PROFILE",
        fixed_lot=0.0,
        risk_percent=0.0,
        risk_amount=0.0,
        custom_magic=0,
        comment="",
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            INSERT INTO profile_mt5_accounts
            (
                profile_id,
                mt5_account_id,
                enabled,
                priority,
                execution_mode,
                risk_mode,
                fixed_lot,
                risk_percent,
                risk_amount,
                custom_magic,
                comment
            )
            VALUES
            (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                profile_id,
                mt5_account_id,
                int(bool(enabled)),
                priority,
                execution_mode,
                risk_mode,
                fixed_lot,
                risk_percent,
                risk_amount,
                custom_magic,
                comment,
            ),
        )

        database_manager.commit()

        return cursor.lastrowid

    # =====================================================
    # UPDATE
    # =====================================================

    def update(
        self,
        row_id,
        priority,
        enabled,
        execution_mode,
        risk_mode,
        fixed_lot,
        risk_percent,
        risk_amount,
        custom_magic,
        comment,
    ):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            UPDATE profile_mt5_accounts
            SET
                priority=?,
                enabled=?,
                execution_mode=?,
                risk_mode=?,
                fixed_lot=?,
                risk_percent=?,
                risk_amount=?,
                custom_magic=?,
                comment=?
            WHERE id=?
            """,
            (
                priority,
                int(bool(enabled)),
                execution_mode,
                risk_mode,
                fixed_lot,
                risk_percent,
                risk_amount,
                custom_magic,
                comment,
                row_id,
            ),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # =====================================================
    # DELETE
    # =====================================================

    def delete(self, row_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            DELETE FROM profile_mt5_accounts
            WHERE id=?
            """,
            (row_id,),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # =====================================================
    # HELPERS
    # =====================================================

    def exists(
        self,
        profile_id,
        account_id,
    ):

        return (
            self.get_account(
                profile_id,
                account_id,
            )
            is not None
        )

    def count(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM profile_mt5_accounts
            WHERE profile_id=?
            """,
            (profile_id,),
        )

        return cursor.fetchone()[0]


profile_mt5_repository = ProfileMT5Repository()