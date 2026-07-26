from __future__ import annotations

import json
from datetime import datetime

from services.operational_data import OperationalData


PIPELINE_STAGES = (
    "CSV", "INTERNAL", "VALIDATION", "PERSISTENCE", "TELEGRAM",
    "ROUTING", "RISK", "PREFLIGHT", "RESULT",
)

SENSITIVE_METADATA_KEYS = {
    "password", "api_hash", "api_id", "bot_token", "token", "secret",
    "mt5_password", "phone", "session", "session_name",
}


def sanitize_metadata(value):
    """Remove credentials recursively before operational persistence."""
    if isinstance(value, dict):
        return {
            str(key): sanitize_metadata(item)
            for key, item in value.items()
            if str(key).strip().lower() not in SENSITIVE_METADATA_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_metadata(item) for item in value]
    return value


class SignalTraceService:
    """Correlates existing signal, publication, operation and log records."""

    def __init__(self, data=None):
        self.data = data or OperationalData()

    def decisions(self, *, limit=50, offset=0, source=None, result=None):
        limit = min(max(int(limit), 1), 200)
        offset = max(int(offset), 0)
        filters, params = [], []
        if source:
            filters.append("UPPER(signal.source)=?")
            params.append(str(source).upper())
        if result:
            filters.append(
                "(UPPER(signal.status)=? OR UPPER(signal.execution_decision)=?)"
            )
            params.extend((str(result).upper(), str(result).upper()))
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        params.extend((limit, offset))
        rows = self.data.rows(
            f"""
            SELECT signal.id, signal.external_signal_id, signal.source,
                   signal.symbol, signal.profile_id, signal.status,
                   signal.rejection_reason, signal.execution_decision,
                   signal.created_at, signal.received_at, signal.metadata,
                   publication.id AS publication_id,
                   publication.status AS telegram_status,
                   operation.id AS operation_id,
                   operation.status AS operation_status
            FROM signals signal
            LEFT JOIN telegram_publications publication
              ON publication.signal_id=signal.id
            LEFT JOIN operations operation ON operation.signal_id=signal.id
            {where}
            GROUP BY signal.id
            ORDER BY signal.id DESC LIMIT ? OFFSET ?
            """,
            tuple(params),
        )
        for row in rows:
            metadata = self._json(row.pop("metadata", "{}"))
            row["profile"] = metadata.get("routed_profiles") or row["profile_id"]
            row["result"] = self._result(row, metadata)
            row["duration_ms"] = metadata.get("duration_ms")
        return rows

    def trace(self, signal_id):
        signal = self.data.row("SELECT * FROM signals WHERE id=?", (signal_id,))
        if not signal:
            return None
        metadata = self._json(signal.get("metadata"))
        events = self._persisted_events(signal_id)
        publications = self.data.rows(
            "SELECT * FROM telegram_publications WHERE signal_id=? ORDER BY id",
            (signal_id,),
        )
        operations = self.data.rows(
            "SELECT * FROM operations WHERE signal_id=? ORDER BY id",
            (signal_id,),
        )
        logs = self.data.rows(
            """
            SELECT id, level, module, message, created_at FROM logs
            WHERE message LIKE ? OR message LIKE ?
            ORDER BY id LIMIT 200
            """,
            (f"%INTERNAL:%:{signal.get('external_signal_id')}%",
             f"%signal_id={signal_id}%"),
        )
        stages = {name: self._stage(name, "PENDING") for name in PIPELINE_STAGES}
        self._infer(stages, signal, metadata, publications, operations, logs)
        for event in events:
            stage = str(event["stage"]).upper()
            if stage in stages:
                stages[stage].update({
                    "status": str(event["status"]).upper(),
                    "started_at": event["timestamp"],
                    "finished_at": event["timestamp"],
                    "duration_ms": event["duration_ms"],
                    "detail": self._json(event["metadata"]).get("detail", ""),
                    "reason": event["reason"] or "",
                    "reference": event["id"],
                })
        return {
            "signal": signal,
            "stages": [stages[name] for name in PIPELINE_STAGES],
            "publications": publications,
            "operations": operations,
            "events": events,
            "logs": logs,
        }

    def recent_activity(
        self, *, limit=100, offset=0, level=None, component=None, signal_id=None
    ):
        limit = min(max(int(limit), 1), 200)
        offset = max(int(offset), 0)
        where, params = [], []
        if level:
            where.append("UPPER(level)=?")
            params.append(str(level).upper())
        if component:
            where.append("module LIKE ?")
            params.append(f"%{component}%")
        if signal_id:
            where.append("message LIKE ?")
            params.append(f"%signal_id={signal_id}%")
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params.extend((limit, offset))
        return self.data.rows(
            f"""
            SELECT id, level, module, message, created_at
            FROM logs {clause} ORDER BY id DESC LIMIT ? OFFSET ?
            """,
            tuple(params),
        )

    def record_event(self, **event):
        """Persist a minimal, sanitized event when the explicit schema exists."""
        if not self.data.table_exists("operational_events"):
            return None
        connection = self.data.connection
        if connection is None:
            from database.database_manager import database_manager

            connection = database_manager.connect()
        metadata = sanitize_metadata(event.get("metadata") or {})
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO operational_events(
                    signal_id, external_signal_id, source, profile_id,
                    operation_id, telegram_publication_id, terminal_id,
                    account_id, timestamp, stage, status, reason,
                    duration_ms, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP),
                          ?, ?, ?, ?, ?)
                """,
                (
                    event.get("signal_id"), event.get("external_signal_id"),
                    event.get("source"), event.get("profile_id"),
                    event.get("operation_id"),
                    event.get("telegram_publication_id"),
                    event.get("terminal_id"), event.get("account_id"),
                    event.get("timestamp"), event["stage"], event["status"],
                    event.get("reason"), event.get("duration_ms"),
                    json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                ),
            )
        return cursor.lastrowid

    def _persisted_events(self, signal_id):
        if not self.data.table_exists("operational_events"):
            return []
        return self.data.rows(
            """
            SELECT * FROM operational_events
            WHERE signal_id=? ORDER BY timestamp, id
            """,
            (signal_id,),
        )

    @staticmethod
    def _json(value):
        try:
            return json.loads(value or "{}")
        except (TypeError, ValueError):
            return {}

    @staticmethod
    def _stage(name, status):
        return {
            "stage": name, "status": status, "started_at": "", "finished_at": "",
            "duration_ms": None, "detail": "", "reason": "", "reference": "",
        }

    def _infer(self, stages, signal, metadata, publications, operations, logs):
        created = signal.get("detected_at") or signal.get("received_at") or signal.get("created_at")
        stages["CSV"].update(status="SUCCESS", started_at=created, finished_at=created)
        stages["INTERNAL"].update(
            status="SUCCESS" if str(signal.get("source")).upper() == "INTERNAL" else "SKIPPED",
            started_at=created, finished_at=created,
            reference=signal.get("external_signal_id") or "",
        )
        status = str(signal.get("status") or "").upper()
        rejected = bool(signal.get("rejection_reason"))
        stages["VALIDATION"].update(
            status="BLOCKED" if rejected else "SUCCESS",
            reason=signal.get("rejection_reason") or "",
        )
        stages["PERSISTENCE"].update(status="SUCCESS", reference=signal["id"])
        if publications:
            publication = publications[-1]
            published = str(publication["status"]).upper()
            stages["TELEGRAM"].update(
                status="SUCCESS" if published == "SENT" else "FAILED",
                reason=publication.get("last_error") or "",
                reference=publication["id"],
                finished_at=publication.get("sent_at") or publication.get("updated_at"),
            )
        else:
            stages["TELEGRAM"]["status"] = "SKIPPED"
        routing = str(metadata.get("routing_status") or "")
        stages["ROUTING"].update(
            status="SUCCESS" if routing == "ROUTED" else (
                "BLOCKED" if routing == "NO_ELIGIBLE_PROFILES" else "SKIPPED"
            ),
            reason=metadata.get("routing_error", ""),
        )
        attempts = metadata.get("routing_attempts") or []
        flattened = " ".join(json.dumps(item) for item in attempts).upper()
        stages["RISK"]["status"] = (
            "BLOCKED" if "RISK_REJECTED" in flattened else
            ("SUCCESS" if attempts else "SKIPPED")
        )
        stages["PREFLIGHT"]["status"] = (
            "BLOCKED" if "PREFLIGHT" in flattened and "BLOCK" in flattened else
            ("SUCCESS" if operations else "SKIPPED")
        )
        if operations:
            operation = operations[-1]
            op_status = str(operation["status"]).upper()
            stages["RESULT"].update(
                status="SUCCESS" if op_status in {
                    "SIMULATED", "SENT", "FILLED", "OPEN", "CLOSED"
                } else "FAILED",
                detail=op_status,
                reference=operation["id"],
            )
        elif status == "FAILED":
            stages["RESULT"].update(status="FAILED", reason=signal.get("rejection_reason") or "")
        elif routing == "NO_ELIGIBLE_PROFILES":
            stages["RESULT"].update(status="SKIPPED", reason=routing)
        else:
            stages["RESULT"]["status"] = "PENDING"

    @staticmethod
    def _result(row, metadata):
        if row.get("operation_status"):
            return str(row["operation_status"]).upper()
        if row.get("telegram_status") == "SENT":
            return "PUBLISHED"
        routing = metadata.get("routing_status")
        if routing:
            return routing
        return str(row.get("execution_decision") or row.get("status") or "PERSISTED").upper()
