from dataclasses import fields

from database.database_manager import database_manager
from models.mt5_terminal import MT5Terminal


_FIELDS = {item.name for item in fields(MT5Terminal)}


class MT5TerminalRepository:
    """Repository activated only after the explicit terminal migration."""

    def _available(self):
        return database_manager.table_exists("mt5_terminals")

    def get_all(self):
        if not self._available():
            return []
        rows = database_manager.execute(
            "SELECT * FROM mt5_terminals ORDER BY name"
        ).fetchall()
        return [
            MT5Terminal(**{key: value for key, value in dict(row).items()
                           if key in _FIELDS})
            for row in rows
        ]

    def get_by_id(self, terminal_id):
        if not self._available():
            return None
        row = database_manager.execute(
            "SELECT * FROM mt5_terminals WHERE id=?", (terminal_id,)
        ).fetchone()
        if row is None:
            return None
        return MT5Terminal(
            **{key: value for key, value in dict(row).items() if key in _FIELDS}
        )

    def save(self, terminal):
        if not self._available():
            raise RuntimeError(
                "La migración explícita del gestor de terminales está pendiente."
            )
        values = (
            terminal.name.strip(), terminal.broker.strip(),
            terminal.executable_path.strip(), terminal.data_path.strip(),
            terminal.catalog_id.strip(), terminal.role.strip().upper(),
            int(bool(terminal.active)), int(bool(terminal.portable)),
            int(bool(terminal.auto_start)),
        )
        if terminal.id is None:
            cursor = database_manager.execute(
                """
                INSERT INTO mt5_terminals(
                    name, broker, executable_path, data_path, catalog_id,
                    role, active, portable, auto_start
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                values,
            )
            terminal.id = cursor.lastrowid
        else:
            database_manager.execute(
                """
                UPDATE mt5_terminals SET
                    name=?, broker=?, executable_path=?, data_path=?,
                    catalog_id=?, role=?, active=?, portable=?, auto_start=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                values + (terminal.id,),
            )
        database_manager.commit()
        return terminal

    def set_runtime_status(self, terminal_id, status, process_id=None):
        if not self._available():
            return False
        cursor = database_manager.execute(
            """
            UPDATE mt5_terminals
            SET connection_status=?, process_id=?, last_seen_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (str(status).upper(), process_id, terminal_id),
        )
        database_manager.commit()
        return cursor.rowcount > 0


mt5_terminal_repository = MT5TerminalRepository()
