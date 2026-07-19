from database.database_manager import database_manager
from models.profile import Profile


class ProfileTelegramChannelRepository:

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