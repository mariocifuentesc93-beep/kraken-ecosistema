from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from services.operational_data import OperationalData


def _utcnow():
    return datetime.now(timezone.utc)


class OperationalHealthService:
    """Builds a read-only health snapshot; it never starts a component."""

    def __init__(self, data=None, runtime_provider=None, now_provider=None):
        self.data = data or OperationalData()
        self.runtime_provider = runtime_provider
        self.now = now_provider or _utcnow

    def snapshot(self):
        now = self.now()
        runtime = self._runtime()
        scanner = self.scanner_health(now)
        profiles = self.profile_health()
        terminals = self.terminal_health()
        cards = {
            "Kraken Runtime": self._card(
                self._runtime_state(runtime), str(getattr(runtime, "last_error", "") or "")
            ),
            "INTERNAL": self._card(
                self._internal_state(runtime), "Fuente de señales INTERNAL"
            ),
            "Telegram": self._card(
                self._telegram_state(runtime), "Cliente de publicación y escucha"
            ),
            "SQLite": self._sqlite_card(),
            "Scanner": scanner["card"],
            "Routing": self._routing_card(profiles),
            "Risk Engine": self._log_health("Risk", "RISK"),
            "Execution Preflight": self._log_health(
                "ExecutionPreflight", "PREFLIGHT"
            ),
        }
        return {
            "updated_at": now.isoformat(timespec="seconds"),
            "cards": cards,
            "scanner": scanner,
            "profiles": profiles,
            "terminals": terminals,
        }

    def _runtime(self):
        if self.runtime_provider:
            return self.runtime_provider()
        try:
            from services.runtime_coordinator import runtime_coordinator

            return runtime_coordinator.get_status()
        except Exception:
            return None

    @staticmethod
    def _runtime_state(runtime):
        state = str(getattr(getattr(runtime, "state", None), "value", "") or "")
        if state == "RUNNING":
            return "RUNNING"
        if state == "ERROR":
            return "DEGRADED"
        return "STOPPED"

    @staticmethod
    def _internal_state(runtime):
        state = str(getattr(runtime, "internal_state", "") or "").upper()
        if state in {"ACTIVE", "RUNNING"}:
            return "ACTIVE"
        if state == "ERROR":
            return "ERROR"
        return "STOPPED"

    @staticmethod
    def _telegram_state(runtime):
        state = str(getattr(runtime, "telegram_state", "") or "").upper()
        if state in {"CONNECTED", "AUTHORIZED", "RUNNING"}:
            return "CONNECTED"
        if state == "ERROR":
            return "ERROR"
        return "DISCONNECTED"

    def _sqlite_card(self):
        try:
            result = self.data.scalar("PRAGMA quick_check", default="ERROR")
            return self._card("AVAILABLE" if result == "ok" else "ERROR", str(result))
        except Exception as error:
            return self._card("BUSY" if "locked" in str(error).lower() else "ERROR", str(error))

    def _log_health(self, module, prefix):
        row = self.data.row(
            """
            SELECT level, message, created_at FROM logs
            WHERE module LIKE ? ORDER BY id DESC LIMIT 1
            """,
            (f"%{module}%",),
        )
        if not row:
            return self._card("READY", "Sin errores recientes")
        level = str(row["level"] or "").upper()
        state = "ERROR" if level in {"ERROR", "CRITICAL"} else (
            "DEGRADED" if level == "WARNING" else "READY"
        )
        return self._card(state, row["message"], row["created_at"])

    def scanner_health(self, now=None):
        now = now or self.now()
        settings = dict(
            (row["key"], row["value"])
            for row in self.data.rows(
                "SELECT key, value FROM settings WHERE key LIKE 'internal.scanner.%'"
            )
        )
        enabled = str(settings.get("internal.scanner.enabled", "0")) == "1"
        output = Path(settings.get("internal.scanner.output_directory", ""))
        try:
            threshold = max(
                1, int(settings.get("internal.scanner.stale_after_minutes", "30"))
            )
        except (TypeError, ValueError):
            threshold = 30
        files = []
        inaccessible = False
        if output:
            try:
                files = sorted(
                    output.glob("Kraken_BMSP_*.csv"),
                    key=lambda item: item.stat().st_mtime,
                    reverse=True,
                )
            except (OSError, PermissionError):
                inaccessible = True
        latest = files[0] if files else None
        modified = (
            datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc)
            if latest else None
        )
        age_minutes = (
            max(0.0, (now - modified).total_seconds() / 60.0)
            if modified else None
        )
        terminal_id = settings.get("internal.scanner.mt5_terminal_id")
        terminal = None
        if terminal_id:
            terminal = self.data.row(
                "SELECT * FROM mt5_terminals WHERE id=?", (terminal_id,)
            )
        process_state = str((terminal or {}).get("process_status") or "STOPPED").upper()
        scanner_state = str((terminal or {}).get("scanner_status") or "INACTIVE").upper()
        if not enabled:
            state, detail = "STOPPED", "Scanner global deshabilitado"
        elif inaccessible or (output and not output.is_dir()):
            state, detail = "CONFLICT", "Carpeta CSV inaccesible"
        elif process_state != "RUNNING":
            state, detail = "STOPPED", "Proceso del terminal detenido"
        elif scanner_state == "CONFLICT":
            state, detail = "CONFLICT", "Conflicto de asociación del Scanner"
        elif latest is None:
            state, detail = "STALE", "CSV nunca detectado"
        elif age_minutes is not None and age_minutes > threshold:
            state, detail = "STALE", f"Sin actualización durante {age_minutes:.0f} min"
        else:
            state, detail = "RUNNING", "Actividad CSV dentro del umbral"
        return {
            "card": self._card(state, detail, modified.isoformat() if modified else None),
            "enabled": enabled,
            "terminal_id": terminal_id,
            "directory": str(output),
            "latest_file": latest.name if latest else "",
            "last_modified": modified.isoformat(timespec="seconds") if modified else "",
            "age_minutes": age_minutes,
            "files_observed": len(files),
            "last_bmsp_id": self._last_internal_id(),
            "stale_after_minutes": threshold,
        }

    def _last_internal_id(self):
        row = self.data.row(
            """
            SELECT external_signal_id FROM signals
            WHERE UPPER(source)='INTERNAL'
            ORDER BY id DESC LIMIT 1
            """
        )
        return (row or {}).get("external_signal_id", "")

    def terminal_health(self):
        return self.data.rows(
            """
            SELECT terminal.id, terminal.name, terminal.active,
                   terminal.process_status, terminal.can_trade,
                   terminal.can_scan, terminal.detected_login,
                   terminal.account_match_status,
                   terminal.trading_connection_status,
                   terminal.scanner_status, terminal.last_seen_at,
                   GROUP_CONCAT(account.login) AS expected_login
            FROM mt5_terminals terminal
            LEFT JOIN mt5_accounts account
              ON account.mt5_terminal_id=terminal.id
            GROUP BY terminal.id ORDER BY terminal.id
            """
        )

    def profile_health(self):
        rows = self.data.rows(
            """
            SELECT profile.id, profile.name, profile.active, profile.enabled,
                   profile.signal_source_mode, profile.execution_mode,
                   profile.default_mt5_account AS account_id,
                   profile.mt5_terminal_id, profile.catalog_id,
                   account.name AS account_name,
                   terminal.name AS terminal_name,
                   terminal.account_match_status,
                   (SELECT COUNT(*) FROM symbols symbol
                    WHERE symbol.profile_id=profile.id AND symbol.enabled=1)
                    AS enabled_symbols
            FROM profiles profile
            LEFT JOIN mt5_accounts account
              ON account.id=profile.default_mt5_account
            LEFT JOIN mt5_terminals terminal
              ON terminal.id=COALESCE(profile.mt5_terminal_id, account.mt5_terminal_id)
            ORDER BY profile.name
            """
        )
        for row in rows:
            row["eligibility_reason"] = self._eligibility(row)
            row["eligible"] = row["eligibility_reason"] == "READY"
        return rows

    @staticmethod
    def _eligibility(row):
        if not row["active"] or not row["enabled"]:
            return "PROFILE_DISABLED"
        if str(row["execution_mode"]).upper() == "OFF":
            return "EXECUTION_MODE_OFF"
        if str(row["signal_source_mode"]).upper() not in {"INTERNAL", "BOTH"}:
            return "SOURCE_NOT_INTERNAL"
        if not row["account_id"]:
            return "NO_ACCOUNT"
        if not row["mt5_terminal_id"]:
            return "NO_TERMINAL"
        if not row["enabled_symbols"]:
            return "NO_SYMBOLS"
        if str(row["account_match_status"]).upper() == "MISMATCH":
            return "ACCOUNT_MISMATCH"
        return "READY"

    def _routing_card(self, profiles):
        if any(row["eligible"] for row in profiles):
            return self._card("READY", "Existe al menos un perfil elegible")
        return self._card("NO_ELIGIBLE_PROFILES", "No existen perfiles elegibles")

    def _card(self, state, detail="", updated_at=None):
        return {
            "state": state,
            "updated_at": updated_at or self.now().isoformat(timespec="seconds"),
            "detail": str(detail or "")[:220],
            "warning": str(detail or "")[:220] if state in {
                "ERROR", "DEGRADED", "BLOCKED", "CONFLICT", "STALE",
                "DISCONNECTED", "NO_ELIGIBLE_PROFILES",
            } else "",
        }
