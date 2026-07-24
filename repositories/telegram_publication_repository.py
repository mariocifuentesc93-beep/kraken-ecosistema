"""Persistencia inyectable e idempotente de publicaciones Telegram."""

from dataclasses import dataclass
from datetime import datetime
import sqlite3

PENDING = "PENDING"
SENT = "SENT"
FAILED = "FAILED"


@dataclass(frozen=True)
class TelegramPublication:
    id: int
    signal_id: int
    idempotency_key: str
    telegram_account_id: int
    chat_id: int
    status: str
    attempt_count: int
    last_error: str | None
    sent_at: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class PublicationReservation:
    publication: TelegramPublication
    created: bool


class TelegramPublicationRepository:
    def __init__(self, connection=None):
        self._connection = connection

    def _cursor(self):
        if self._connection is not None:
            return self._connection.cursor()
        from database.database_manager import database_manager
        return database_manager.cursor()

    def _commit(self):
        if self._connection is not None:
            self._connection.commit()
        else:
            from database.database_manager import database_manager
            database_manager.commit()

    @staticmethod
    def _from_row(row):
        if row is None:
            return None
        return TelegramPublication(**dict(row))

    def get(self, idempotency_key, telegram_account_id, chat_id):
        cursor = self._cursor()
        cursor.execute(
            """
            SELECT * FROM telegram_publications
            WHERE idempotency_key=?
              AND telegram_account_id=?
              AND chat_id=?
            """,
            (idempotency_key, telegram_account_id, chat_id),
        )
        return self._from_row(cursor.fetchone())

    def get_or_create(
        self,
        signal_id,
        idempotency_key,
        telegram_account_id,
        chat_id,
    ):
        now = datetime.now().isoformat(timespec="microseconds")
        cursor = self._cursor()
        try:
            cursor.execute(
                """
                INSERT INTO telegram_publications(
                    signal_id, idempotency_key, telegram_account_id,
                    chat_id, status, attempt_count, last_error,
                    sent_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?)
                """,
                (
                    signal_id,
                    idempotency_key,
                    telegram_account_id,
                    chat_id,
                    PENDING,
                    now,
                    now,
                ),
            )
            self._commit()
            return PublicationReservation(
                publication=self.get(
                    idempotency_key,
                    telegram_account_id,
                    chat_id,
                ),
                created=True,
            )
        except sqlite3.IntegrityError:
            if self._connection is not None:
                self._connection.rollback()
            existing = self.get(
                idempotency_key,
                telegram_account_id,
                chat_id,
            )
            if existing is None:
                raise
            return PublicationReservation(existing, created=False)

    def mark_sent(self, publication_id):
        now = datetime.now().isoformat(timespec="microseconds")
        cursor = self._cursor()
        cursor.execute(
            """
            UPDATE telegram_publications
            SET status=?, attempt_count=attempt_count+1,
                last_error=NULL, sent_at=?, updated_at=?
            WHERE id=?
            """,
            (SENT, now, now, publication_id),
        )
        self._commit()
        return self.get_by_id(publication_id)

    def mark_failed(self, publication_id, error):
        now = datetime.now().isoformat(timespec="microseconds")
        cursor = self._cursor()
        cursor.execute(
            """
            UPDATE telegram_publications
            SET status=?, attempt_count=attempt_count+1,
                last_error=?, updated_at=?
            WHERE id=?
            """,
            (FAILED, str(error), now, publication_id),
        )
        self._commit()
        return self.get_by_id(publication_id)

    def get_by_id(self, publication_id):
        cursor = self._cursor()
        cursor.execute(
            "SELECT * FROM telegram_publications WHERE id=?",
            (publication_id,),
        )
        return self._from_row(cursor.fetchone())


telegram_publication_repository = TelegramPublicationRepository()
