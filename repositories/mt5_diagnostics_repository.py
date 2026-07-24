import json
from datetime import datetime

from database.database_manager import database_manager


class MT5DiagnosticsRepository:
    def save_diagnostic(self, report):
        cursor = database_manager.cursor()
        cursor.execute(
            """INSERT INTO mt5_connection_diagnostics(
                account_id, success, terminal_path, account_number, server, details, created_at
            ) VALUES (?,?,?,?,?,?,?)""",
            (report.get("account_id"), int(report.get("success", False)),
             report.get("terminal_path", ""), str(report.get("account", "")),
             report.get("server", ""), json.dumps(report, default=str, ensure_ascii=False),
             report.get("connected_timestamp") or datetime.now().isoformat()),
        )
        database_manager.commit()
        return cursor.lastrowid

    def save_symbol_results(self, diagnostic_id, results):
        cursor = database_manager.cursor()
        cursor.executemany(
            """INSERT INTO mt5_symbol_validations(diagnostic_id, symbol, mt5_symbol, available,
               visible, selectable, tick_available, details, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            [(diagnostic_id, row["symbol"], row["mt5_symbol"], int(row["available"]),
              int(row["visible"]), int(row["selectable"]), int(row["tick_available"]),
              json.dumps(row, default=str, ensure_ascii=False), datetime.now().isoformat())
             for row in results],
        )
        database_manager.commit()

    def latest(self, account_id=None):
        sql, params = "SELECT * FROM mt5_connection_diagnostics", []
        if account_id is not None:
            sql += " WHERE account_id=?"; params.append(account_id)
        cursor = database_manager.cursor()
        cursor.execute(sql + " ORDER BY id DESC LIMIT 1", params)
        row = cursor.fetchone()
        return dict(row) if row else None


mt5_diagnostics_repository = MT5DiagnosticsRepository()
