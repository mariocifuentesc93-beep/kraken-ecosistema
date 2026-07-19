import sqlite3
import threading
from pathlib import Path

from database.schema import create_tables


class DatabaseManager:
    """SQLite connection factory with one connection per calling thread."""

    def __init__(self):
        self.database = Path(__file__).resolve().parent / "kraken.db"
        self._local = threading.local()
        self._initialization_lock = threading.RLock()

    @property
    def connection(self):
        return getattr(self._local, "connection", None)

    def connect(self):
        connection = self.connection
        if connection is not None:
            return connection

        # Schema creation and WAL configuration must not race when a worker
        # starts while the UI thread is opening the application database.
        with self._initialization_lock:
            connection = sqlite3.connect(self.database, check_same_thread=True)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            create_tables(connection)
            self._local.connection = connection
        return connection

    def initialize(self):
        self.connect()

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

    def commit(self):
        self.connect().commit()

    def rollback(self):
        self.connect().rollback()

    def table_exists(self, table_name):
        cursor = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return cursor.fetchone() is not None

    def close(self):
        """Close only the current thread's connection.

        A thread must close its own connection; this avoids handing SQLite
        objects across threads during application shutdown.
        """
        connection = self.connection
        if connection is None:
            return
        connection.close()
        self._local.connection = None

    def backup(self, destination):
        """Create a consistent SQLite backup, including pending WAL changes."""
        target = sqlite3.connect(destination)
        try:
            self.connect().backup(target)
        finally:
            target.close()


database_manager = DatabaseManager()
