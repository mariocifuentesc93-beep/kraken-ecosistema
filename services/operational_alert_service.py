from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from services.operational_data import OperationalData


RECOMMENDATIONS = {
    "SCANNER_STOPPED": "Revise el terminal Scanner en Terminales MT5.",
    "SCANNER_CSV_STALE": "Valide el indicador y la carpeta Common\\Files.",
    "TELEGRAM_DISCONNECTED": "Revise la cuenta en la pantalla Telegram.",
    "DATABASE_UNAVAILABLE": "Revise bloqueo, espacio e integridad de SQLite.",
    "TERMINAL_STOPPED": "Abra la instalación desde Terminales MT5.",
    "ACCOUNT_MISMATCH": "Compruebe la cuenta esperada y detectada.",
    "NO_ELIGIBLE_PROFILES": "Revise fuente, modo, cuenta, terminal y símbolos.",
    "ROUTING_ERROR": "Revise Logs y configuración de perfiles.",
    "RISK_ENGINE_ERROR": "Revise la gestión de riesgo del perfil.",
    "PREFLIGHT_ERROR": "Revise el motivo normalizado del pre-flight.",
    "DUPLICATE_SIGNAL_BLOCKED": "No se requiere acción si la señal ya fue procesada.",
    "PUBLICATION_FAILED": "Revise permisos y conectividad del destino Telegram.",
}


class OperationalAlertService:
    def __init__(self, data=None, connection=None):
        self.data = data or OperationalData(connection)
        self.connection = connection

    def derive(self, health):
        alerts = []
        cards = health.get("cards", {})
        mapping = {
            ("Scanner", "STOPPED"): ("SCANNER_STOPPED", "ERROR"),
            ("Scanner", "STALE"): ("SCANNER_CSV_STALE", "WARNING"),
            ("Telegram", "DISCONNECTED"): ("TELEGRAM_DISCONNECTED", "WARNING"),
            ("SQLite", "ERROR"): ("DATABASE_UNAVAILABLE", "CRITICAL"),
            ("Routing", "NO_ELIGIBLE_PROFILES"): ("NO_ELIGIBLE_PROFILES", "INFO"),
            ("Risk Engine", "ERROR"): ("RISK_ENGINE_ERROR", "ERROR"),
            ("Execution Preflight", "ERROR"): ("PREFLIGHT_ERROR", "ERROR"),
        }
        for (component, state), (kind, severity) in mapping.items():
            card = cards.get(component, {})
            if card.get("state") == state:
                alerts.append(self._alert(kind, severity, component, card.get("detail", "")))
        for terminal in health.get("terminals", []):
            if str(terminal.get("process_status")).upper() == "STOPPED" and terminal.get("active"):
                alerts.append(self._alert(
                    "TERMINAL_STOPPED", "WARNING", "MT5",
                    f"{terminal.get('name')} está detenida", terminal.get("id"),
                ))
            if str(terminal.get("account_match_status")).upper() == "MISMATCH":
                alerts.append(self._alert(
                    "ACCOUNT_MISMATCH", "WARNING", "MT5",
                    f"{terminal.get('name')}: cuenta esperada y detectada no coinciden",
                    terminal.get("id"),
                ))
        patterns = (
            ("DUPLICATE_SIGNAL_BLOCKED", "INFO", "DUPLICATE"),
            ("PUBLICATION_FAILED", "ERROR", "PUBLICATION_FAILED"),
            ("ROUTING_ERROR", "ERROR", "ROUTING_ERROR"),
            ("RISK_ENGINE_ERROR", "ERROR", "RISK_ENGINE_ERROR"),
            ("PREFLIGHT_ERROR", "ERROR", "PREFLIGHT_ERROR"),
        )
        recent = self.data.rows(
            """
            SELECT module, message, MAX(created_at) AS last_seen,
                   COUNT(*) AS occurrences
            FROM logs
            WHERE id >= MAX((SELECT MAX(id)-500 FROM logs), 0)
            GROUP BY module, message
            ORDER BY MAX(id) DESC LIMIT 200
            """
        )
        for kind, severity, marker in patterns:
            matches = [
                row for row in recent
                if marker in str(row.get("message") or "").upper()
            ]
            if not matches:
                continue
            newest = matches[0]
            alert = self._alert(
                kind, severity, newest.get("module") or "Kraken",
                newest.get("message") or kind,
            )
            alert["occurrence_count"] = sum(
                int(row.get("occurrences") or 1) for row in matches
            )
            alert["last_seen_at"] = newest.get("last_seen") or alert["last_seen_at"]
            alerts.append(alert)
        return alerts

    def list(self, *, active_only=False, limit=100):
        if not self.data.table_exists("operational_alerts"):
            return []
        where = "WHERE state='ACTIVE'" if active_only else ""
        return self.data.rows(
            f"""
            SELECT * FROM operational_alerts {where}
            ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'ERROR' THEN 2
                 WHEN 'WARNING' THEN 3 ELSE 4 END, last_seen_at DESC
            LIMIT ?
            """,
            (min(max(int(limit), 1), 200),),
        )

    def record(self, alert):
        """Explicitly persist/group an alert when the optional schema exists."""
        if not self.data.table_exists("operational_alerts"):
            return None
        connection = self.connection
        if connection is None:
            from database.database_manager import database_manager

            connection = database_manager.connect()
        with connection:
            connection.execute(
                """
                INSERT INTO operational_alerts(
                    fingerprint, alert_type, severity, state, first_seen_at,
                    last_seen_at, occurrence_count, component, message,
                    recommended_action, metadata
                ) VALUES (?, ?, ?, 'ACTIVE', ?, ?, 1, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    state='ACTIVE', last_seen_at=excluded.last_seen_at,
                    occurrence_count=operational_alerts.occurrence_count+1,
                    severity=excluded.severity, message=excluded.message,
                    recommended_action=excluded.recommended_action,
                    resolved_at=NULL
                """,
                (
                    alert["fingerprint"], alert["alert_type"], alert["severity"],
                    alert["first_seen_at"], alert["last_seen_at"],
                    alert["component"], alert["message"],
                    alert["recommended_action"], json.dumps(alert.get("metadata", {})),
                ),
            )
        return alert["fingerprint"]

    def resolve(self, fingerprint):
        if not self.data.table_exists("operational_alerts"):
            return False
        connection = self.connection
        if connection is None:
            from database.database_manager import database_manager

            connection = database_manager.connect()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with connection:
            cursor = connection.execute(
                """
                UPDATE operational_alerts SET state='RESOLVED', resolved_at=?,
                    last_seen_at=? WHERE fingerprint=? AND state='ACTIVE'
                """,
                (now, now, fingerprint),
            )
        return cursor.rowcount > 0

    @staticmethod
    def _alert(kind, severity, component, message, subject=None):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        identity = f"{kind}|{component}|{subject or ''}"
        fingerprint = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return {
            "fingerprint": fingerprint, "alert_type": kind,
            "severity": severity, "state": "ACTIVE", "first_seen_at": now,
            "last_seen_at": now, "occurrence_count": 1,
            "component": component, "message": message,
            "recommended_action": RECOMMENDATIONS.get(kind, "Revise los Logs."),
            "metadata": {"subject": subject} if subject is not None else {},
        }
