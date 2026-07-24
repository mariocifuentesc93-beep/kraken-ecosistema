from database.database_manager import database_manager
from models.profile import Profile


class ProfileTelegramChannelRepository:

    def create_channel(self, chat_id, title, profile_id=None, account_id=None):
        if profile_id is None or account_id is None:
            raise ValueError("profile_id and account_id are required")

        cursor = database_manager.cursor()
        cursor.execute(
            """
            INSERT INTO profile_telegram_channels
            (profile_id, account_id, chat_id, title, enabled, priority)
            VALUES (?, ?, ?, ?, 1, 1)
            """,
            (profile_id, account_id, chat_id, title),
        )
        database_manager.commit()
        return cursor.lastrowid

    def get_channel(self, chat_id):
        cursor = database_manager.cursor()
        cursor.execute(
            """
            SELECT * FROM profile_telegram_channels
            WHERE chat_id=? ORDER BY priority LIMIT 1
            """,
            (chat_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_by_id(self, channel_id):
        cursor = database_manager.cursor()
        cursor.execute(
            "SELECT * FROM profile_telegram_channels WHERE id=?", (channel_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_channels(self):
        cursor = database_manager.cursor()
        cursor.execute(
            "SELECT * FROM profile_telegram_channels ORDER BY priority, title"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_available_channels(self, account_id):
        """Return distinct configured chats for the selected Telegram account."""
        if account_id is None:
            return []
        cursor = database_manager.cursor()
        cursor.execute(
            """
            SELECT chat_id, MAX(title) AS title, MAX(username) AS username
            FROM profile_telegram_channels
            WHERE account_id=?
            GROUP BY chat_id
            ORDER BY title, chat_id
            """,
            (account_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def set_profile_channel(self, profile_id, account_id, channel):
        """Assign one configured channel to a profile without affecting other profiles."""
        cursor = database_manager.cursor()
        cursor.execute(
            "DELETE FROM profile_telegram_channels WHERE profile_id=?",
            (profile_id,),
        )
        if channel is not None and account_id is not None:
            cursor.execute(
                """
                INSERT INTO profile_telegram_channels
                (profile_id, account_id, chat_id, title, username, enabled, priority)
                VALUES (?, ?, ?, ?, ?, 1, 1)
                """,
                (
                    profile_id,
                    account_id,
                    channel["chat_id"],
                    channel.get("title", ""),
                    channel.get("username", ""),
                ),
            )
        database_manager.commit()

    def set_channel_enabled(self, chat_id, enabled):
        cursor = database_manager.cursor()
        cursor.execute(
            "UPDATE profile_telegram_channels SET enabled=? WHERE chat_id=?",
            (int(bool(enabled)), chat_id),
        )
        database_manager.commit()
        return cursor.rowcount > 0

    def update_channel(self, channel_id, chat_id, title, username, profile_id, account_id,
                       enabled, priority):
        cursor = database_manager.cursor()
        cursor.execute(
            """
            UPDATE profile_telegram_channels
            SET chat_id=?, title=?, username=?, profile_id=?, account_id=?,
                enabled=?, priority=?
            WHERE id=?
            """,
            (chat_id, title, username, profile_id, account_id, int(bool(enabled)),
             priority, channel_id),
        )
        database_manager.commit()
        return cursor.rowcount > 0

    def delete_channel(self, channel_id):
        cursor = database_manager.cursor()
        cursor.execute(
            "DELETE FROM profile_telegram_channels WHERE id=?", (channel_id,)
        )
        database_manager.commit()
        return cursor.rowcount > 0

    # =====================================================
    # CONSULTAS
    # =====================================================

    def get_profiles(self, chat_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT
                p.*

            FROM profiles p

            INNER JOIN profile_telegram_channels c
                ON c.profile_id = p.id

            WHERE
                c.chat_id = ?
                AND c.enabled = 1
                AND p.enabled = 1

            ORDER BY
                c.priority ASC,
                p.name ASC
            """,
            (chat_id,),
        )

        return [
            Profile(**dict(row))
            for row in cursor.fetchall()
        ]

    # =====================================================
    # HELPERS
    # =====================================================

    def has_profiles(self, chat_id):

        return len(self.get_profiles(chat_id)) > 0

    def count_profiles(self, chat_id):

        cursor = database_manager.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM profile_telegram_channels
            WHERE
                chat_id=?
                AND enabled=1
            """,
            (chat_id,),
        )

        return cursor.fetchone()[0]


profile_telegram_channel_repository = (
    ProfileTelegramChannelRepository()
)
