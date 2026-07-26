"""Small read-only query gateway used by operational monitoring services."""

from __future__ import annotations

from contextlib import contextmanager

from database.database_manager import database_manager


class OperationalData:
    def __init__(self, connection=None):
        self.connection = connection

    @contextmanager
    def cursor(self):
        connection = self.connection or database_manager.connect()
        yield connection.cursor()

    def table_exists(self, name):
        with self.cursor() as cursor:
            return cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (name,),
            ).fetchone() is not None

    def rows(self, sql, params=()):
        with self.cursor() as cursor:
            return [dict(row) for row in cursor.execute(sql, params).fetchall()]

    def row(self, sql, params=()):
        with self.cursor() as cursor:
            value = cursor.execute(sql, params).fetchone()
            return dict(value) if value is not None else None

    def scalar(self, sql, params=(), default=0):
        with self.cursor() as cursor:
            row = cursor.execute(sql, params).fetchone()
            return default if row is None else row[0]
