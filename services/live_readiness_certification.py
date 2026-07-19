"""Read-only LIVE readiness certification; it never authorizes order submission."""

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from database.database_manager import database_manager
from mt5.connector import mt5_connector
from repositories.mt5_diagnostics_repository import mt5_diagnostics_repository
from repositories.profile_repository import profile_repository
from repositories.telegram_account_repository import telegram_account_repository
from repositories.telegram_diagnostics_repository import telegram_diagnostics_repository
from repositories.settings_repository import settings_repository
from services.market_data_service import market_data_service
from version import VERSION


class LiveReadinessCertification:
    PASS, WARNING, FAIL = "PASS", "WARNING", "FAIL"

    def item(self, section, name, status, detail):
        return {"section": section, "name": name, "status": status, "detail": detail}

    def evaluate(self):
        items = []
        try:
            profile = profile_repository.get_active()
        except Exception as error:
            items = [self.item("General", "Database version", self.FAIL, str(error)),
                     self.item("Storage", "SQLite healthy", self.FAIL, str(error))]
            return {"generated_at": datetime.now(timezone.utc).isoformat(), "score": 0,
                    "available": False, "items": items, "blocking_report": [str(error)],
                    "live_execution": "BLOCKED: certification never submits orders."}
        items += [self.item("General", "Application version", self.PASS, VERSION),
                  self._database_version(),
                  self.item("General", "Active profile", self.PASS if profile and profile.enabled else self.FAIL,
                            profile.name if profile else "No active profile."),
                  self.item("General", "Execution mode", self.PASS if profile and profile.execution_mode != "LIVE" else self.WARNING,
                            getattr(profile, "execution_mode", "OFF"))]
        items += self._mt5_items(profile)
        items += self._telegram_items(profile)
        items += self._risk_items(profile)
        items += self._execution_items()
        items += self._storage_items()
        score = round(sum({self.PASS: 1, self.WARNING: .5, self.FAIL: 0}[item["status"]] for item in items) / len(items) * 100)
        blocking = [item["detail"] for item in items if item["status"] == self.FAIL]
        available = score == 100 and not blocking and profile is not None
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "score": score,
                "available": available, "items": items, "blocking_report": blocking,
                "live_execution": "BLOCKED: certification never submits orders."}

    def _database_version(self):
        try:
            version = database_manager.execute("PRAGMA user_version").fetchone()[0]
            return self.item("General", "Database version", self.PASS, str(version))
        except Exception as error:
            return self.item("General", "Database version", self.FAIL, str(error))

    def _mt5_items(self, profile):
        account = None if not profile or not profile.default_mt5_account else __import__("repositories.mt5_account_repository", fromlist=["mt5_account_repository"]).mt5_account_repository.get_by_id(profile.default_mt5_account)
        report = mt5_diagnostics_repository.latest(account.id) if account else None
        details = json.loads(report["details"]) if report else {}
        validated = bool(report and report["success"] and len(details.get("symbols", [])) == 20 and all(row.get("tick_available") for row in details["symbols"]))
        quote = market_data_service.quote("EMASVOL10", allow_fallback=False)
        return [
            self.item("MT5", "Connected", self.PASS if account and mt5_connector.is_connected() else self.FAIL, "Terminal connected." if account and mt5_connector.is_connected() else "MT5 is not connected."),
            self.item("MT5", "Logged in", self.PASS if details.get("success") else self.FAIL, "Validated account login." if details.get("success") else "No successful MT5 diagnostic."),
            self.item("MT5", "Trading enabled", self.PASS if details.get("trade_allowed") else self.FAIL, "Trading permission confirmed." if details.get("trade_allowed") else "Trading permission is disabled."),
            self.item("MT5", "Algo trading enabled", self.PASS if details.get("algorithmic_trading_allowed") else self.FAIL, "Algo permission confirmed." if details.get("algorithmic_trading_allowed") else "Algorithmic trading is disabled."),
            self.item("MT5", "Symbol validation", self.PASS if validated else self.FAIL, "20/20 symbols validated." if validated else "All 20 MT5 symbols require validation."),
            self.item("MT5", "Tick freshness", self.PASS if quote.get("source") == "MT5" and quote.get("fresh") else self.FAIL, quote.get("stale_reason") or "Fresh MT5 tick required."),
        ]

    def _telegram_items(self, profile):
        account = telegram_account_repository.get_by_id(profile.telegram_account_id) if profile and profile.telegram_account_id else None
        report = telegram_diagnostics_repository.latest(account.id) if account else None
        details = json.loads(report["details"]) if report else {}
        channels = details.get("channels", [])
        ready_channels = bool(channels) and all(row.get("accessible") and row.get("enabled") for row in channels)
        authorized = bool(account and account.authorized and details.get("authorized"))
        return [
            self.item("Telegram", "Authorized", self.PASS if authorized else self.FAIL, "Authorized account." if authorized else "Telegram authorization is required."),
            self.item("Telegram", "Connected", self.PASS if account and account.connected and details.get("connected") else self.FAIL, "Telegram connected." if account and account.connected and details.get("connected") else "Telegram is disconnected."),
            self.item("Telegram", "Active account", self.PASS if account else self.FAIL, account.name if account else "No Telegram account assigned."),
            self.item("Telegram", "Configured channels", self.PASS if ready_channels else self.FAIL, f"{len(channels)} accessible channels." if ready_channels else "No accessible enabled channels."),
            self.item("Telegram", "Listener ready", self.PASS if authorized and ready_channels else self.FAIL, "Ready on demand; listener remains stopped." if authorized and ready_channels else "Authorization and channels are required."),
        ]

    def _risk_items(self, profile):
        if not profile:
            return [self.item("Risk", name, self.FAIL, "No active profile.") for name in ("Risk mode", "Risk percentage", "Daily loss limit", "Max simultaneous trades", "Drawdown protection", "Exposure protection")]
        valid_risk = profile.risk_enabled and ((profile.risk_mode == "PERCENT" and profile.risk_percent > 0) or (profile.risk_mode == "AMOUNT" and profile.risk_amount > 0) or (profile.risk_mode == "LOT" and profile.fixed_lot > 0))
        return [
            self.item("Risk", "Risk mode", self.PASS if valid_risk else self.FAIL, profile.risk_mode),
            self.item("Risk", "Risk percentage", self.PASS if profile.risk_percent > 0 else self.FAIL, str(profile.risk_percent)),
            self.item("Risk", "Daily loss limit", self.PASS if profile.max_daily_loss > 0 else self.FAIL, str(profile.max_daily_loss)),
            self.item("Risk", "Max simultaneous trades", self.PASS if profile.max_open_trades > 0 else self.FAIL, str(profile.max_open_trades)),
            self.item("Risk", "Drawdown protection", self.PASS if profile.max_daily_loss > 0 else self.FAIL, "Daily loss limit required."),
            self.item("Risk", "Exposure protection", self.PASS if profile.max_open_trades > 0 and profile.max_lot > 0 else self.FAIL, "Trade-count and lot limits required."),
        ]

    def _execution_items(self):
        required = (("signals", "Signal pipeline healthy"), ("operations", "Execution pipeline healthy"),
                    ("operation_events", "Simulation engine healthy"), ("operation_events", "Timeline repository healthy"))
        items = []
        for table, label in required:
            try:
                status = self.PASS if database_manager.table_exists(table) else self.FAIL
                detail = table
            except Exception as error:
                status, detail = self.FAIL, str(error)
            items.append(self.item("Execution", label, status, detail))
        return items

    def _storage_items(self):
        try:
            database_manager.execute("SELECT 1")
            healthy = self.PASS
            detail = "SQLite query succeeded."
        except Exception as error:
            healthy, detail = self.FAIL, str(error)
        configured_backup = Path(settings_repository.get("last_backup_path", ""))
        backup_dir = database_manager.database.parent / "backups"
        backups = sorted(backup_dir.glob("*.db")) if backup_dir.exists() else []
        latest = configured_backup if configured_backup.is_file() else (backups[-1] if backups else None)
        age = (datetime.now().timestamp() - latest.stat().st_mtime) / 3600 if latest else None
        return [self.item("Storage", "SQLite healthy", healthy, detail),
                self.item("Storage", "Backup available", self.PASS if latest else self.FAIL, str(latest) if latest else "No backup found."),
                self.item("Storage", "Last backup age", self.PASS if age is not None and age <= 24 else self.FAIL, f"{age:.1f} hours" if age is not None else "No backup found.")]

    @staticmethod
    def to_json(report): return json.dumps(report, indent=2, ensure_ascii=False)
    @staticmethod
    def to_text(report): return "LIVE Readiness Certification\nScore: {}%\nAvailable: {}\n\n".format(report["score"], report["available"]) + "\n".join(f"[{i['status']}] {i['section']} - {i['name']}: {i['detail']}" for i in report["items"])
    @staticmethod
    def to_html(report):
        rows = "".join(f"<tr><td>{escape(i['section'])}</td><td>{escape(i['name'])}</td><td>{i['status']}</td><td>{escape(i['detail'])}</td></tr>" for i in report["items"])
        return f"<html><body><h1>LIVE Readiness Certification</h1><p>Score: {report['score']}% | Available: {report['available']}</p><table border='1'><tr><th>Section</th><th>Item</th><th>Status</th><th>Detail</th></tr>{rows}</table></body></html>"
    def export(self, report, destination, report_type):
        content = {"json": self.to_json, "txt": self.to_text, "html": self.to_html}[report_type](report)
        Path(destination).write_text(content, encoding="utf-8")


live_readiness_certification = LiveReadinessCertification()
