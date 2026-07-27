from datetime import datetime
from dataclasses import fields

from models.profile import Profile
from database.database_manager import database_manager


PROFILE_FIELDS = {item.name for item in fields(Profile)}


def _profile_from_row(row):
    values = dict(row)
    return Profile(
        **{
            key: value
            for key, value in values.items()
            if key in PROFILE_FIELDS
        }
    )


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
                max_risk_percent,
                risk_amount,
                fixed_lot,
                min_lot,
                max_lot,

                max_daily_loss,
                max_daily_profit,
                max_drawdown,
                max_open_trades,
                min_signal_score,

                execution_mode,
                tp_level,
                tp1_management,
                execute_market,

                magic_number,
                comment,
                deviation,

                total_operations,
                winning_operations,
                losing_operations,
                breakeven_operations,
                total_profit,
                total_loss,
                net_profit,
                win_rate,

                created_at,
                updated_at
            )

            VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                profile.max_risk_percent,
                profile.risk_amount,
                profile.fixed_lot,
                profile.min_lot,
                profile.max_lot,

                profile.max_daily_loss,
                profile.max_daily_profit,
                profile.max_drawdown,
                profile.max_open_trades,
                profile.min_signal_score,

                profile.execution_mode,
                profile.tp_level,
                profile.tp1_management,
                int(profile.execute_market),

                profile.magic_number,
                profile.comment,
                profile.deviation,

                profile.total_operations,
                profile.winning_operations,
                profile.losing_operations,
                profile.breakeven_operations,
                profile.total_profit,
                profile.total_loss,
                profile.net_profit,
                profile.win_rate,

                profile.created_at,
                profile.updated_at,
            ),
        )

        database_manager.commit()

        profile.id = cursor.lastrowid

        self._save_terminal_context(profile)
        self._notify_change(profile.id)

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
                max_risk_percent=?,
                risk_amount=?,
                fixed_lot=?,
                min_lot=?,
                max_lot=?,

                max_daily_loss=?,
                max_daily_profit=?,
                max_drawdown=?,
                max_open_trades=?,
                min_signal_score=?,

                execution_mode=?,
                tp_level=?,
                tp1_management=?,
                execute_market=?,

                magic_number=?,
                comment=?,
                deviation=?,

                total_operations=?,
                winning_operations=?,
                losing_operations=?,
                breakeven_operations=?,
                total_profit=?,
                total_loss=?,
                net_profit=?,
                win_rate=?,

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
                profile.max_risk_percent,
                profile.risk_amount,
                profile.fixed_lot,
                profile.min_lot,
                profile.max_lot,

                profile.max_daily_loss,
                profile.max_daily_profit,
                profile.max_drawdown,
                profile.max_open_trades,
                profile.min_signal_score,

                profile.execution_mode,
                profile.tp_level,
                profile.tp1_management,
                int(profile.execute_market),

                profile.magic_number,
                profile.comment,
                profile.deviation,

                profile.total_operations,
                profile.winning_operations,
                profile.losing_operations,
                profile.breakeven_operations,
                profile.total_profit,
                profile.total_loss,
                profile.net_profit,
                profile.win_rate,

                profile.updated_at,

                profile.id,
            ),
        )

        database_manager.commit()
        self._notify_change(profile.id)

        return profile

    # ---------------------------------------------------------

    def delete(self, profile_id):

        cursor = database_manager.cursor()

        cursor.execute(
            "DELETE FROM profiles WHERE id=?",
            (profile_id,),
        )

        database_manager.commit()

        changed = cursor.rowcount > 0
        if changed:
            self._notify_change(profile_id)
        return changed

    @staticmethod
    def _notify_change(profile_id):
        from services.routing_configuration_service import (
            routing_configuration_service,
        )
        routing_configuration_service.notify_changed(profile_id, "profile")

    def _save_terminal_context(self, profile):
        columns = {
            row[1] for row in database_manager.execute(
                "PRAGMA table_info(profiles)"
            ).fetchall()
        }
        assignments = []
        values = []
        if "mt5_terminal_id" in columns:
            assignments.append("mt5_terminal_id=?")
            values.append(profile.mt5_terminal_id)
        if "catalog_id" in columns:
            assignments.append("catalog_id=?")
            values.append(profile.catalog_id)
        if not assignments or profile.id is None:
            return
        values.append(profile.id)
        database_manager.execute(
            f"UPDATE profiles SET {', '.join(assignments)} WHERE id=?",
            tuple(values),
        )
        database_manager.commit()

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

        return _profile_from_row(row)

    # ---------------------------------------------------------

    def get_active(self):

        profiles = self.get_active_profiles()
        return profiles[0] if profiles else None

    # ---------------------------------------------------------

    def get_active_profiles(self):
        """Return every profile currently eligible to process a signal."""

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT *

            FROM profiles

            WHERE
                active=1
                AND enabled=1

            ORDER BY name
            """
        )

        return [_profile_from_row(row) for row in cursor.fetchall()]

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
            _profile_from_row(row)
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
            _profile_from_row(row)
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
                AND p.active=1
                AND p.enabled=1

            ORDER BY p.name
            """,
            (chat_id,),
        )

        return [
            _profile_from_row(row)
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
                active=1
                AND enabled=1
                AND signal_source_mode IN ('INTERNAL', 'BOTH')
                AND execution_mode IN ('SIMULATION', 'DEMO', 'LIVE')
            ORDER BY name
            """
        )
        return [_profile_from_row(row) for row in cursor.fetchall()]

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
