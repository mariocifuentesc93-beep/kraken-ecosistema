import json
from datetime import datetime

from database.database_manager import database_manager


class TelegramDiagnosticsRepository:
    def save_diagnostic(self, report):
        cursor = database_manager.cursor()
        cursor.execute(
            """INSERT INTO telegram_diagnostics(account_id, status, success, details, created_at)
               VALUES (?,?,?,?,?)""",
            (report.get("account_id"), report["status"], int(report.get("success", False)),
             json.dumps(report, default=str, ensure_ascii=False), report["connected_timestamp"]),
        )
        database_manager.commit()
        return cursor.lastrowid

    def save_channel_results(self, diagnostic_id, results):
        cursor = database_manager.cursor()
        cursor.executemany(
            """INSERT INTO telegram_channel_validations(
               diagnostic_id, channel_id, chat_id, title, accessible, enabled, details, created_at
            ) VALUES (?,?,?,?,?,?,?,?)""",
            [(diagnostic_id, row["channel_id"], str(row["chat_id"]), row.get("title", ""),
              int(row["accessible"]), int(row["enabled"]),
              json.dumps(row, default=str, ensure_ascii=False), datetime.now().isoformat())
             for row in results],
        )
        database_manager.commit()

    def latest(self, account_id=None):
        sql, params = "SELECT * FROM telegram_diagnostics", []
        if account_id is not None:
            sql += " WHERE account_id=?"; params.append(account_id)
        cursor = database_manager.cursor()
        cursor.execute(sql + " ORDER BY id DESC LIMIT 1", params)
        row = cursor.fetchone()
        return dict(row) if row else None


telegram_diagnostics_repository = TelegramDiagnosticsRepository()
