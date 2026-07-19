import sqlite3
from pathlib import Path

from database.schema import create_tables


class DatabaseManager:

    def __init__(self):

        root = Path(__file__).resolve().parent

        self.database = root / "kraken.db"

        self.connection = None

    # =====================================================
    # CONNECTION
    # =====================================================

    def connect(self):

        if self.connection is not None:

            return self.connection

        self.connection = sqlite3.connect(
            self.database,
            check_same_thread=False,
        )

        self.connection.row_factory = sqlite3.Row

        self.connection.execute(

            "PRAGMA foreign_keys = ON"

        )

        self.connection.execute(

            "PRAGMA journal_mode = WAL"

        )

        self.connection.execute(

            "PRAGMA synchronous = NORMAL"

        )

        create_tables(self.connection)

        return self.connection

    # =====================================================
    # INITIALIZATION
    # =====================================================

    def initialize(self):

        self.connect()

    # =====================================================
    # DATABASE ACCESS
    # =====================================================

    def cursor(self):

        return self.connect().cursor()

    def execute(self, sql, params=()):

        cursor = self.cursor()

        cursor.execute(sql, params)

        return cursor

    def executemany(self, sql, values):

        cursor = self.cursor()

        cursor.executemany(sql, values)

        return cursor

    # =====================================================
    # TRANSACTIONS
    # =====================================================

    def commit(self):

        self.connect().commit()

    def rollback(self):

        self.connect().rollback()

    # =====================================================
    # UTILITIES
    # =====================================================

    def table_exists(self, table_name):

        cursor = self.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name=?
            """,
            (table_name,),
        )

        return cursor.fetchone() is not None

    def close(self):

        if self.connection is None:

            return

        self.connection.close()

        self.connection = None

    def backup(self, destination):
        """Create a consistent SQLite backup, including pending WAL changes."""
        target = sqlite3.connect(destination)
        try:
            self.connect().backup(target)
        finally:
            target.close()


database_manager = DatabaseManager()
