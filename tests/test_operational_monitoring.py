import json
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from database.operational_monitoring_migration import downgrade, upgrade
from services.operational_alert_service import OperationalAlertService
from services.operational_data import OperationalData
from services.operational_health_service import OperationalHealthService
from services.operational_metrics_service import OperationalMetricsService
from services.signal_trace_service import (
    PIPELINE_STAGES,
    SignalTraceService,
    sanitize_metadata,
)


@pytest.fixture
def monitoring_connection(tmp_path):
    connection = sqlite3.connect(tmp_path / "monitoring.db")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE profiles(
            id INTEGER PRIMARY KEY, name TEXT, active INTEGER, enabled INTEGER,
            signal_source_mode TEXT, execution_mode TEXT,
            default_mt5_account INTEGER, mt5_terminal_id INTEGER,
            catalog_id TEXT
        );
        CREATE TABLE mt5_accounts(
            id INTEGER PRIMARY KEY, name TEXT, login INTEGER,
            mt5_terminal_id INTEGER
        );
        CREATE TABLE mt5_terminals(
            id INTEGER PRIMARY KEY, name TEXT, active INTEGER,
            process_status TEXT, can_trade INTEGER, can_scan INTEGER,
            detected_login TEXT, account_match_status TEXT,
            trading_connection_status TEXT, scanner_status TEXT,
            last_seen_at TEXT
        );
        CREATE TABLE symbols(
            id INTEGER PRIMARY KEY, profile_id INTEGER, enabled INTEGER
        );
        CREATE TABLE signals(
            id INTEGER PRIMARY KEY, external_signal_id TEXT, source TEXT,
            symbol TEXT, profile_id INTEGER, status TEXT,
            rejection_reason TEXT, execution_decision TEXT,
            created_at TEXT, received_at TEXT, detected_at TEXT,
            metadata TEXT, idempotency_key TEXT
        );
        CREATE TABLE telegram_accounts(id INTEGER PRIMARY KEY);
        CREATE TABLE telegram_publications(
            id INTEGER PRIMARY KEY, signal_id INTEGER, telegram_account_id INTEGER,
            idempotency_key TEXT, chat_id INTEGER, status TEXT, attempt_count INTEGER,
            last_error TEXT, sent_at TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE operations(
            id INTEGER PRIMARY KEY, signal_id INTEGER, profile_id INTEGER,
            mt5_account_id INTEGER, status TEXT, opened_at TEXT
        );
        CREATE TABLE logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT, level TEXT, module TEXT,
            message TEXT, created_at TEXT
        );
        CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);

        INSERT INTO mt5_terminals VALUES(
            1, 'Bridge', 1, 'RUNNING', 1, 1, '99', 'MATCH',
            'CONNECTED', 'ACTIVE', '2026-07-26 12:00:00'
        );
        INSERT INTO mt5_accounts VALUES(10, 'Demo', 99, 1);
        INSERT INTO profiles VALUES(
            1, 'Demo', 1, 1, 'INTERNAL', 'SIMULATION', 10, 1,
            'BRIDGE_SYNTHETICS'
        );
        INSERT INTO symbols VALUES(1, 1, 1);
        INSERT INTO signals VALUES(
            100, '12882', 'INTERNAL', 'EMASVOL10', 1, 'SIMULATED', '',
            'SIMULATED', '2026-07-26 12:00:00', '2026-07-26 12:00:00',
            '2026-07-26 12:00:00',
            '{"routing_status":"ROUTED","routed_profiles":[{"id":1,"name":"Demo"}],"routing_attempts":[{"decision":"SIMULATED"}]}',
            'INTERNAL:EMASVOL10:12882'
        );
        INSERT INTO telegram_publications VALUES(
            200, 100, 1, 'INTERNAL:EMASVOL10:12882', -100, 'SENT', 1,
            NULL, '2026-07-26 12:00:02', '2026-07-26 12:00:01',
            '2026-07-26 12:00:02'
        );
        INSERT INTO operations VALUES(
            300, 100, 1, 10, 'SIMULATED', '2026-07-26 12:00:03'
        );
        INSERT INTO logs(level,module,message,created_at) VALUES
            ('INFO','Internal','DETECTED | INTERNAL:EMASVOL10:12882','2026-07-26 12:00:00'),
            ('INFO','Telegram','TELEGRAM_PUBLICATION SUCCESS signal_id=100','2026-07-26 12:00:02'),
            ('INFO','Risk','RISK APPROVED signal_id=100','2026-07-26 12:00:02'),
            ('INFO','ExecutionPreflight','PREFLIGHT READY signal_id=100','2026-07-26 12:00:03');
        """
    )
    yield connection
    connection.close()


def data(connection):
    return OperationalData(connection)


def runtime(state="RUNNING", telegram="CONNECTED", internal="ACTIVE", error=""):
    return SimpleNamespace(
        state=SimpleNamespace(value=state),
        telegram_state=telegram,
        internal_state=internal,
        last_error=error,
    )


def scanner_settings(connection, directory, enabled="1", terminal_id="1", stale="30"):
    connection.executemany(
        "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
        (
            ("internal.scanner.enabled", enabled),
            ("internal.scanner.mt5_terminal_id", terminal_id),
            ("internal.scanner.output_directory", str(directory)),
            ("internal.scanner.stale_after_minutes", stale),
        ),
    )
    connection.commit()


def test_internal_active_health(monitoring_connection, tmp_path):
    scanner_settings(monitoring_connection, tmp_path)
    (tmp_path / "Kraken_BMSP_EMASVOL10.csv").write_text("ok", encoding="utf-8")
    result = OperationalHealthService(
        data(monitoring_connection), lambda: runtime()
    ).snapshot()
    assert result["cards"]["INTERNAL"]["state"] == "ACTIVE"
    assert result["cards"]["Scanner"]["state"] == "RUNNING"


def test_telegram_disconnected_health(monitoring_connection):
    result = OperationalHealthService(
        data(monitoring_connection), lambda: runtime(telegram="DISCONNECTED")
    ).snapshot()
    assert result["cards"]["Telegram"]["state"] == "DISCONNECTED"


def test_sqlite_available_health(monitoring_connection):
    result = OperationalHealthService(
        data(monitoring_connection), lambda: runtime()
    ).snapshot()
    assert result["cards"]["SQLite"]["state"] == "AVAILABLE"


def test_stopped_terminal_and_account_mismatch_are_visible(monitoring_connection):
    monitoring_connection.execute(
        """
        UPDATE mt5_terminals SET process_status='STOPPED',
            account_match_status='MISMATCH' WHERE id=1
        """
    )
    result = OperationalHealthService(data(monitoring_connection)).snapshot()
    terminal = result["terminals"][0]
    assert terminal["process_status"] == "STOPPED"
    assert terminal["account_match_status"] == "MISMATCH"


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    (
        ("enabled", 0, "PROFILE_DISABLED"),
        ("execution_mode", "OFF", "EXECUTION_MODE_OFF"),
        ("signal_source_mode", "TELEGRAM", "SOURCE_NOT_INTERNAL"),
        ("default_mt5_account", None, "NO_ACCOUNT"),
        ("mt5_terminal_id", None, "NO_TERMINAL"),
    ),
)
def test_profile_ineligibility_reasons(
    monitoring_connection, field, value, reason
):
    monitoring_connection.execute(f"UPDATE profiles SET {field}=? WHERE id=1", (value,))
    if field == "mt5_terminal_id" and value is None:
        monitoring_connection.execute(
            "UPDATE mt5_accounts SET mt5_terminal_id=NULL WHERE id=10"
        )
    profile = OperationalHealthService(data(monitoring_connection)).profile_health()[0]
    assert profile["eligibility_reason"] == reason


def test_profile_without_symbols_is_not_eligible(monitoring_connection):
    monitoring_connection.execute("UPDATE symbols SET enabled=0")
    profile = OperationalHealthService(data(monitoring_connection)).profile_health()[0]
    assert profile["eligibility_reason"] == "NO_SYMBOLS"


def test_simulation_internal_profile_is_eligible(monitoring_connection):
    profile = OperationalHealthService(data(monitoring_connection)).profile_health()[0]
    assert profile["eligible"] is True
    assert profile["eligibility_reason"] == "READY"


def test_signal_trace_correlates_complete_pipeline(monitoring_connection):
    trace = SignalTraceService(data(monitoring_connection)).trace(100)
    assert [stage["stage"] for stage in trace["stages"]] == list(PIPELINE_STAGES)
    statuses = {stage["stage"]: stage["status"] for stage in trace["stages"]}
    assert statuses["PERSISTENCE"] == "SUCCESS"
    assert statuses["TELEGRAM"] == "SUCCESS"
    assert statuses["ROUTING"] == "SUCCESS"
    assert statuses["RESULT"] == "SUCCESS"


def test_telegram_is_independent_from_routing(monitoring_connection):
    metadata = json.dumps({"routing_status": "NO_ELIGIBLE_PROFILES"})
    monitoring_connection.execute(
        "UPDATE signals SET metadata=? WHERE id=100", (metadata,)
    )
    stages = {
        row["stage"]: row["status"]
        for row in SignalTraceService(data(monitoring_connection)).trace(100)["stages"]
    }
    assert stages["TELEGRAM"] == "SUCCESS"
    assert stages["ROUTING"] == "BLOCKED"


@pytest.mark.parametrize(
    ("attempt", "stage", "expected"),
    (
        ({"decision": "RISK_REJECTED"}, "RISK", "BLOCKED"),
        ({"decision": "PREFLIGHT_BLOCKED"}, "PREFLIGHT", "BLOCKED"),
    ),
)
def test_blocked_pipeline_stages(
    monitoring_connection, attempt, stage, expected
):
    metadata = json.dumps({
        "routing_status": "ROUTED", "routing_attempts": [attempt]
    })
    monitoring_connection.execute(
        "UPDATE signals SET metadata=? WHERE id=100", (metadata,)
    )
    stages = {
        row["stage"]: row["status"]
        for row in SignalTraceService(data(monitoring_connection)).trace(100)["stages"]
    }
    assert stages[stage] == expected


def test_simulation_is_represented(monitoring_connection):
    trace = SignalTraceService(data(monitoring_connection)).trace(100)
    result = next(row for row in trace["stages"] if row["stage"] == "RESULT")
    assert result["detail"] == "SIMULATED"


@pytest.mark.parametrize(
    "secret", ("password", "api_hash", "bot_token", "mt5_password")
)
def test_operational_event_metadata_does_not_require_credentials(
    monitoring_connection, secret
):
    upgrade(monitoring_connection)
    columns = {
        row["name"] for row in monitoring_connection.execute(
            "PRAGMA table_info(operational_events)"
        )
    }
    assert secret not in columns


def test_operational_event_metadata_is_sanitized_recursively(monitoring_connection):
    upgrade(monitoring_connection)
    service = SignalTraceService(data(monitoring_connection))
    event_id = service.record_event(
        signal_id=100,
        stage="RISK",
        status="SUCCESS",
        metadata={
            "lot": 0.1,
            "password": "forbidden",
            "nested": {"bot_token": "forbidden", "risk": 5},
        },
    )
    metadata = json.loads(
        monitoring_connection.execute(
            "SELECT metadata FROM operational_events WHERE id=?", (event_id,)
        ).fetchone()[0]
    )
    assert metadata == {"lot": 0.1, "nested": {"risk": 5}}


def test_alerts_are_grouped_and_resolved(monitoring_connection):
    upgrade(monitoring_connection)
    service = OperationalAlertService(
        data(monitoring_connection), monitoring_connection
    )
    alert = service._alert("ACCOUNT_MISMATCH", "WARNING", "MT5", "Mismatch", 1)
    service.record(alert)
    service.record(alert)
    rows = service.list()
    assert len(rows) == 1
    assert rows[0]["occurrence_count"] == 2
    assert service.resolve(alert["fingerprint"]) is True
    assert service.list()[0]["state"] == "RESOLVED"


def test_csv_stale_and_never_detected(monitoring_connection, tmp_path):
    scanner_settings(monitoring_connection, tmp_path, stale="1")
    service = OperationalHealthService(data(monitoring_connection))
    assert service.scanner_health()["card"]["state"] == "STALE"
    path = tmp_path / "Kraken_BMSP_LIONX25.csv"
    path.write_text("old", encoding="utf-8")
    old = time.time() - 3600
    os.utime(path, (old, old))
    assert service.scanner_health()["card"]["state"] == "STALE"


def test_scanner_stopped(monitoring_connection, tmp_path):
    scanner_settings(monitoring_connection, tmp_path)
    monitoring_connection.execute(
        "UPDATE mt5_terminals SET process_status='STOPPED' WHERE id=1"
    )
    result = OperationalHealthService(data(monitoring_connection)).scanner_health()
    assert result["card"]["state"] == "STOPPED"


@pytest.mark.parametrize("period", ("SESSION", "TODAY", "7D", "30D"))
def test_operational_metrics_periods(monitoring_connection, period):
    metrics = OperationalMetricsService(
        data(monitoring_connection),
        session_started_at=datetime(2026, 7, 26, tzinfo=timezone.utc),
    ).calculate(period)
    assert metrics["period"] == period
    assert set(metrics) >= {
        "signals_detected", "signals_persisted", "telegram_publications",
        "simulations", "risk_rejections", "preflight_blocks",
        "orders_sent", "orders_filled", "failures", "duplicates_blocked",
        "average_processing_ms",
    }


def test_decision_pagination_and_incremental_activity(monitoring_connection):
    service = SignalTraceService(data(monitoring_connection))
    assert len(service.decisions(limit=1, offset=0)) == 1
    assert service.decisions(limit=1, offset=1) == []
    first = service.recent_activity(limit=2, offset=0)
    second = service.recent_activity(limit=2, offset=2)
    assert {row["id"] for row in first}.isdisjoint({row["id"] for row in second})


def test_migration_is_explicit_idempotent_and_reversible(monitoring_connection):
    assert not data(monitoring_connection).table_exists("operational_events")
    upgrade(monitoring_connection)
    upgrade(monitoring_connection)
    assert data(monitoring_connection).table_exists("operational_events")
    assert data(monitoring_connection).table_exists("operational_alerts")
    downgrade(monitoring_connection)
    assert not data(monitoring_connection).table_exists("operational_events")
    assert not data(monitoring_connection).table_exists("operational_alerts")
    assert monitoring_connection.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 1


def test_monitoring_page_is_read_only_and_refresh_is_non_blocking(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QPushButton
    from dashboard.pages.operational_monitoring_page import OperationalMonitoringPage

    app = QApplication.instance() or QApplication([])
    page = OperationalMonitoringPage(auto_refresh=False)
    button_texts = {button.text() for button in page.findChildren(QPushButton)}
    forbidden = {"Enviar orden", "Activar DEMO", "Activar LIVE", "Modificar riesgo"}
    assert button_texts.isdisjoint(forbidden)
    started = time.perf_counter()
    page.refresh()
    assert time.perf_counter() - started < 0.25
    deadline = time.time() + 5
    while page._thread is not None and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert page.refresh_button.isEnabled()
    page.close()


def test_importing_monitoring_migration_has_no_database_side_effect(tmp_path):
    database = tmp_path / "untouched.db"
    database.write_bytes(b"not-a-database")
    before = database.read_bytes()
    __import__("database.operational_monitoring_migration")
    assert database.read_bytes() == before
