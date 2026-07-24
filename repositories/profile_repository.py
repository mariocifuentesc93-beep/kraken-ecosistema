from datetime import datetime

from models.profile import Profile
from database.database_manager import database_manager


class ProfileRepository:

    # ---------------------------------------------------------

    def create(self, profile: Profile):

        now = datetime.now().isoformat(
            sep=" ",
            timespec="seconds",
        )

        profile.created_at = now
        profile.updated_at = now

        cursor = database_manager.cursor()

        cursor.execute(
            """
            INSERT INTO profiles
            (
                name,
                description,

                color,
                icon,

                active,
                enabled,

                operation_mode,
                signal_source_mode,

                telegram_account_id,
                telegram_channel_id,

                default_mt5_account,

                risk_enabled,
                risk_mode,
                risk_percent,
                risk_amount,
                fixed_lot,
                min_lot,
                max_lot,

                max_daily_loss,
                max_daily_profit,
                max_open_trades,

                execution_mode,
                tp_level,
                execute_market,

                magic_number,
                comment,
                deviation,

                created_at,
                updated_at
            )

            VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                profile.name,
                profile.description,

                profile.color,
                profile.icon,

                int(profile.active),
                int(profile.enabled),

                profile.operation_mode,
                profile.signal_source_mode,

                profile.telegram_account_id,
                profile.telegram_channel_id,

                profile.default_mt5_account,

                int(profile.risk_enabled),
                profile.risk_mode,
                profile.risk_percent,
                profile.risk_amount,
                profile.fixed_lot,
                profile.min_lot,
                profile.max_lot,

                profile.max_daily_loss,
                profile.max_daily_profit,
                profile.max_open_trades,

                profile.execution_mode,
                profile.tp_level,
                int(profile.execute_market),

                profile.magic_number,
                profile.comment,
                profile.deviation,

                profile.created_at,
                profile.updated_at,
            ),
        )

        database_manager.commit()

        profile.id = cursor.lastrowid

        return profile

    # ---------------------------------------------------------

    def update(self, profile: Profile):

        profile.updated_at = datetime.now().isoformat(
            sep=" ",
            timespec="seconds",
        )

        cursor = database_manager.cursor()

        cursor.execute(
            """
            UPDATE profiles

            SET

                name=?,
                description=?,

                color=?,
                icon=?,

                active=?,
                enabled=?,

                operation_mode=?,
                signal_source_mode=?,

                telegram_account_id=?,
                telegram_channel_id=?,

                default_mt5_account=?,

                risk_enabled=?,
                risk_mode=?,
                risk_percent=?,
                risk_amount=?,
                fixed_lot=?,
                min_lot=?,
                max_lot=?,

                max_daily_loss=?,
                max_daily_profit=?,
                max_open_trades=?,

                execution_mode=?,
                tp_level=?,
                execute_market=?,

                magic_number=?,
                comment=?,
                deviation=?,

                updated_at=?

            WHERE id=?
            """,
            (
                profile.name,
                profile.description,

                profile.color,
                profile.icon,

                int(profile.active),
                int(profile.enabled),

                profile.operation_mode,
                profile.signal_source_mode,

                profile.telegram_account_id,
                profile.telegram_channel_id,

                profile.default_mt5_account,

                int(profile.risk_enabled),
                profile.risk_mode,
                profile.risk_percent,
                profile.risk_amount,
                profile.fixed_lot,
                profile.min_lot,
                profile.max_lot,

                profile.max_daily_loss,
                profile.max_daily_profit,
                profile.max_open_trades,

                profile.execution_mode,
                profile.tp_level,
                int(profile.execute_market),

                profile.magic_number,
                profile.comment,
                profile.deviation,

                profile.updated_at,

                profile.id,
            ),
        )

        database_manager.commit()

        return profile

    # ---------------------------------------------------------

    def delete(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            "DELETE FROM profiles WHERE id=?",
            (profile_id,),
        )

        database_manager.commit()

        return cursor.rowcount > 0

    # ---------------------------------------------------------

    def get_by_id(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            "SELECT * FROM profiles WHERE id=?",
            (profile_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return Profile(**dict(row))

    # ---------------------------------------------------------

    def get_active(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM profiles

            WHERE
                active=1
                AND enabled=1

            LIMIT 1
            """
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return Profile(**dict(row))

    # ---------------------------------------------------------

    def exists(self, profile_id):

        return self.get_by_id(profile_id) is not None

    # ---------------------------------------------------------

    def get_all(self):

        cursor = database_manager.cursor()

        cursor.execute(
            "SELECT * FROM profiles ORDER BY name"
        )

        return [
            Profile(**dict(row))
            for row in cursor.fetchall()
        ]

    # ---------------------------------------------------------

    def get_enabled(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM profiles

            WHERE enabled=1

            ORDER BY name
            """
        )

        return [
            Profile(**dict(row))
            for row in cursor.fetchall()
        ]

    # ---------------------------------------------------------

    def get_profiles_by_chat(self, chat_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT DISTINCT p.*

            FROM profiles p

            INNER JOIN profile_telegram_channels ptc

                ON p.id=ptc.profile_id

            WHERE
                ptc.chat_id=?
                AND ptc.enabled=1
                AND p.enabled=1

            ORDER BY p.name
            """,
            (chat_id,),
        )

        return [
            Profile(**dict(row))
            for row in cursor.fetchall()
        ]

    # ---------------------------------------------------------

    def get_internal_profiles(self):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *
            FROM profiles
            WHERE
                enabled=1
                AND signal_source_mode IN ('INTERNAL', 'BOTH')
            ORDER BY name
            """
        )

        return [
            Profile(**dict(row))
            for row in cursor.fetchall()
        ]

    # ---------------------------------------------------------

    def duplicate(self, profile_id):

        profile = self.get_by_id(profile_id)

        if profile is None:
            return None

        profile.id = None
        profile.name = f"{profile.name} (Copia)"

        return self.create(profile)

    # ---------------------------------------------------------

    def clear(self):

        cursor = database_manager.cursor()

        cursor.execute(
            "DELETE FROM profiles"
        )

        database_manager.commit()

    # ---------------------------------------------------------

    def count(self):

        cursor = database_manager.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM profiles"
        )

        return cursor.fetchone()[0]


profile_repository = ProfileRepository()
