from dataclasses import fields

from database.database_manager import database_manager
from models.mt5_terminal import MT5Terminal


_FIELDS = {item.name for item in fields(MT5Terminal)}


class MT5TerminalRepository:
    """Repository activated only after the explicit terminal migration."""

    def _available(self):
        return database_manager.table_exists("mt5_terminals")

    def _columns(self):
        if not self._available():
            return set()
        return {
            row[1]
            for row in database_manager.execute(
                "PRAGMA table_info(mt5_terminals)"
            ).fetchall()
        }

    def capabilities_available(self):
        return {"can_trade", "can_scan"} <= self._columns()

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

    def get_active(self):
        if not self._available():
            return []
        rows = database_manager.execute(
            "SELECT * FROM mt5_terminals WHERE active=1 ORDER BY name"
        ).fetchall()
        return [
            MT5Terminal(
                **{
                    key: value
                    for key, value in dict(row).items()
                    if key in _FIELDS
                }
            )
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

    def get_scanner_capable(self, active_only=True):
        if not self._available():
            return []
        columns = self._columns()
        if "can_scan" in columns:
            where = "can_scan=1"
        else:
            where = "UPPER(role)='SCANNER'"
        if active_only:
            where += " AND active=1"
        rows = database_manager.execute(
            f"SELECT * FROM mt5_terminals WHERE {where} ORDER BY name"
        ).fetchall()
        return [
            MT5Terminal(
                **{
                    key: value
                    for key, value in dict(row).items()
                    if key in _FIELDS
                }
            )
            for row in rows
        ]

    def save(self, terminal):
        if not self._available():
            raise RuntimeError(
                "La migración explícita del gestor de terminales está pendiente."
            )
        legacy_values = (
            terminal.name.strip(), terminal.broker.strip(),
            terminal.executable_path.strip(), terminal.data_path.strip(),
            terminal.catalog_id.strip(), terminal.role.strip().upper(),
            int(bool(terminal.active)), int(bool(terminal.portable)),
            int(bool(terminal.auto_start)),
        )
        columns = self._columns()
        has_capabilities = {"can_trade", "can_scan"} <= columns
        capability_values = (
            int(bool(terminal.can_trade)),
            int(bool(terminal.can_scan)),
            str(terminal.process_status or "STOPPED").upper(),
            str(
                terminal.trading_connection_status or "NOT_VALIDATED"
            ).upper(),
            str(terminal.scanner_status or "INACTIVE").upper(),
            str(terminal.account_match_status or "NOT_VALIDATED").upper(),
            (
                str(terminal.detected_login).strip()
                if terminal.detected_login is not None
                else None
            ),
            (
                str(terminal.detected_server).strip()
                if terminal.detected_server is not None
                else None
            ),
        )
        if terminal.id is None:
            if has_capabilities:
                cursor = database_manager.execute(
                    """
                    INSERT INTO mt5_terminals(
                        name, broker, executable_path, data_path, catalog_id,
                        role, active, portable, auto_start,
                        can_trade, can_scan, process_status,
                        trading_connection_status, scanner_status,
                        account_match_status, detected_login, detected_server
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    legacy_values + capability_values,
                )
            else:
                cursor = database_manager.execute(
                    """
                    INSERT INTO mt5_terminals(
                        name, broker, executable_path, data_path, catalog_id,
                        role, active, portable, auto_start
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    legacy_values,
                )
            terminal.id = cursor.lastrowid
        else:
            if has_capabilities:
                database_manager.execute(
                    """
                    UPDATE mt5_terminals SET
                        name=?, broker=?, executable_path=?, data_path=?,
                        catalog_id=?, role=?, active=?, portable=?, auto_start=?,
                        can_trade=?, can_scan=?, process_status=?,
                        trading_connection_status=?, scanner_status=?,
                        account_match_status=?, detected_login=?,
                        detected_server=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    legacy_values + capability_values + (terminal.id,),
                )
            else:
                database_manager.execute(
                    """
                    UPDATE mt5_terminals SET
                        name=?, broker=?, executable_path=?, data_path=?,
                        catalog_id=?, role=?, active=?, portable=?, auto_start=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    legacy_values + (terminal.id,),
                )
        database_manager.commit()
        return terminal

    def set_runtime_status(self, terminal_id, status, process_id=None):
        if not self._available():
            return False
        normalized = str(status).upper()
        if "process_status" in self._columns():
            cursor = database_manager.execute(
                """
                UPDATE mt5_terminals
                SET connection_status=?, process_status=?, process_id=?,
                    last_seen_at=CURRENT_TIMESTAMP,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (normalized, normalized, process_id, terminal_id),
            )
        else:
            cursor = database_manager.execute(
                """
                UPDATE mt5_terminals
                SET connection_status=?, process_id=?,
                    last_seen_at=CURRENT_TIMESTAMP,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (normalized, process_id, terminal_id),
            )
        database_manager.commit()
        return cursor.rowcount > 0

    def set_diagnostic_status(
        self,
        terminal_id,
        *,
        process_status,
        trading_connection_status="NOT_VALIDATED",
        scanner_status="INACTIVE",
        account_match_status="NOT_VALIDATED",
        detected_login=None,
        detected_server=None,
        process_id=None,
    ):
        required = {
            "process_status",
            "trading_connection_status",
            "scanner_status",
            "account_match_status",
            "detected_login",
            "detected_server",
        }
        if not required <= self._columns():
            raise RuntimeError(
                "La migración explícita de capacidades MT5 está pendiente."
            )
        cursor = database_manager.execute(
            """
            UPDATE mt5_terminals
            SET process_status=?, trading_connection_status=?,
                scanner_status=?, account_match_status=?,
                detected_login=?, detected_server=?, process_id=?,
                last_seen_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                str(process_status).upper(),
                str(trading_connection_status).upper(),
                str(scanner_status).upper(),
                str(account_match_status).upper(),
                (
                    str(detected_login).strip()
                    if detected_login is not None
                    else None
                ),
                (
                    str(detected_server).strip()
                    if detected_server is not None
                    else None
                ),
                process_id,
                terminal_id,
            ),
        )
        database_manager.commit()
        return cursor.rowcount > 0


mt5_terminal_repository = MT5TerminalRepository()
