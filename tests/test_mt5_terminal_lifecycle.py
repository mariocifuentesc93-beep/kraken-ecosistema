import os
import sqlite3
from pathlib import Path

import pytest

from database.mt5_installation_manager_migration import (
    upgrade as installation_upgrade,
)
from database.mt5_terminal_capabilities_migration import (
    upgrade as capability_upgrade,
)
from database.schema import create_tables
from models.mt5_account import MT5Account
from models.mt5_terminal import MT5Terminal
from services.mt5_terminal_lifecycle_service import (
    MT5TerminalLifecycleError,
    MT5TerminalLifecycleService,
)


@pytest.fixture
def lifecycle_db():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_tables(connection)
    installation_upgrade(connection)
    capability_upgrade(connection)
    connection.execute("DELETE FROM operations")
    connection.execute("DELETE FROM profiles")
    connection.execute("DELETE FROM mt5_accounts")
    connection.execute("DELETE FROM mt5_terminals")
    connection.execute("DELETE FROM logs")
    connection.execute(
        "UPDATE settings SET value='0' "
        "WHERE key='internal.scanner.enabled'"
    )
    connection.execute(
        "UPDATE settings SET value='' "
        "WHERE key='internal.scanner.mt5_terminal_id'"
    )
    connection.commit()
    notifications = []
    service = MT5TerminalLifecycleService(
        connection,
        notifier=lambda terminal_id, action: notifications.append(
            (terminal_id, action)
        ),
        process_checker=lambda _pid: False,
    )
    yield connection, service, notifications
    connection.close()


def terminal_fixture(tmp_path, **changes):
    install = tmp_path / changes.pop("folder", "MetaTrader 5")
    install.mkdir(exist_ok=True)
    executable = install / "terminal64.exe"
    executable.write_bytes(b"terminal fixture")
    data = tmp_path / changes.pop("data_folder", "D0E820")
    data.mkdir(exist_ok=True)
    values = {
        "name": "Bridge principal",
        "broker": "Bridge Markets",
        "executable_path": str(executable),
        "data_path": str(data),
        "catalog_id": "BRIDGE_SYNTHETICS",
        "can_trade": True,
        "can_scan": True,
        "active": True,
    }
    values.update(changes)
    return MT5Terminal(**values)


def register(lifecycle_db, tmp_path, **changes):
    connection, service, _ = lifecycle_db
    terminal = terminal_fixture(tmp_path, **changes)
    result = service.register(terminal)
    return connection, service, terminal, result


def add_account(connection, *, terminal_id=None, login=7911007):
    cursor = connection.execute(
        """
        INSERT INTO mt5_accounts(
            name,login,password,server,terminal_path,execution_mode,
            mt5_terminal_id
        ) VALUES(?,?,?,?,?,'OFF',?)
        """,
        (
            f"Cuenta {login}",
            login,
            "secret",
            "BridgeMarkets-MT5",
            "C:/terminal64.exe",
            terminal_id,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def test_registers_new_installation_once(lifecycle_db, tmp_path):
    connection, _, terminal, result = register(lifecycle_db, tmp_path)
    assert result.success and terminal.id == result.terminal_id
    assert connection.execute(
        "SELECT COUNT(*) FROM mt5_terminals"
    ).fetchone()[0] == 1
    assert result.changed_fields["can_scan"] == 1


def test_rejects_duplicate_executable_case_insensitively(
    lifecycle_db, tmp_path
):
    _, service, terminal, _ = register(lifecycle_db, tmp_path)
    duplicate = terminal_fixture(
        tmp_path,
        name="Duplicada",
        executable_path=terminal.executable_path.upper(),
    )
    with pytest.raises(MT5TerminalLifecycleError, match="ya está registrada"):
        service.register(duplicate)


def test_edits_name_and_hybrid_capabilities(lifecycle_db, tmp_path):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    result = service.update(
        terminal.id,
        {"name": "Bridge híbrida", "can_trade": False, "can_scan": True},
    )
    row = connection.execute(
        "SELECT name,can_trade,can_scan,role FROM mt5_terminals WHERE id=?",
        (terminal.id,),
    ).fetchone()
    assert tuple(row) == ("Bridge híbrida", 0, 1, "SCANNER")
    assert "name" in result.changed_fields


def test_protects_route_changes_without_explicit_action(
    lifecycle_db, tmp_path
):
    _, service, terminal, _ = register(lifecycle_db, tmp_path)
    with pytest.raises(MT5TerminalLifecycleError, match="rutas"):
        service.update(
            terminal.id, {"executable_path": "C:/other/terminal64.exe"}
        )


def test_explicit_route_change_checks_duplicate(lifecycle_db, tmp_path):
    _, service, first, _ = register(lifecycle_db, tmp_path)
    second = terminal_fixture(
        tmp_path, folder="MetaTrader 5 second", data_folder="SECOND"
    )
    service.register(second)
    with pytest.raises(MT5TerminalLifecycleError, match="pertenece"):
        service.update(
            second.id,
            {"executable_path": first.executable_path},
            allow_path_change=True,
        )


def test_disable_preserves_record_and_turns_off_autostart(
    lifecycle_db, tmp_path
):
    connection, service, terminal, _ = register(
        lifecycle_db, tmp_path, auto_start=True
    )
    result = service.set_enabled(terminal.id, False)
    row = connection.execute(
        "SELECT active,auto_start FROM mt5_terminals WHERE id=?",
        (terminal.id,),
    ).fetchone()
    assert result.success and tuple(row) == (0, 0)


def test_blocks_disabling_global_scanner(lifecycle_db, tmp_path):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    connection.execute(
        "UPDATE settings SET value='1' "
        "WHERE key='internal.scanner.enabled'"
    )
    connection.execute(
        "UPDATE settings SET value=? "
        "WHERE key='internal.scanner.mt5_terminal_id'",
        (str(terminal.id),),
    )
    connection.commit()
    result = service.set_enabled(terminal.id, False)
    assert not result.success
    assert "Scanner global" in result.blocking_reasons[0]
    assert connection.execute(
        "SELECT active FROM mt5_terminals WHERE id=?", (terminal.id,)
    ).fetchone()[0] == 1


def test_sync_detected_login_only_after_explicit_confirmation(
    lifecycle_db, tmp_path
):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    account_id = add_account(
        connection, terminal_id=terminal.id, login=7911007
    )
    with pytest.raises(MT5TerminalLifecycleError, match="confirmación"):
        service.synchronize_account(
            terminal.id,
            "UPDATE_EXPECTED",
            expected_account_id=account_id,
            detected_login=7906571,
            detected_server="BridgeMarkets-MT5",
        )
    assert connection.execute(
        "SELECT login FROM mt5_accounts WHERE id=?", (account_id,)
    ).fetchone()[0] == 7911007


def test_real_case_7906571_updates_account_not_terminal(
    lifecycle_db, tmp_path
):
    connection, service, terminal, _ = register(
        lifecycle_db,
        tmp_path,
        data_path=str(tmp_path / "D0E8209F77C8CF37AD8BF550E51FF075"),
    )
    account_id = add_account(
        connection, terminal_id=terminal.id, login=7911007
    )
    before = connection.execute(
        "SELECT executable_path,data_path FROM mt5_terminals WHERE id=?",
        (terminal.id,),
    ).fetchone()
    service.synchronize_account(
        terminal.id,
        "UPDATE_EXPECTED",
        expected_account_id=account_id,
        detected_login=7906571,
        detected_server="BridgeMarkets-MT5",
        confirmed=True,
    )
    after = connection.execute(
        "SELECT executable_path,data_path FROM mt5_terminals WHERE id=?",
        (terminal.id,),
    ).fetchone()
    assert tuple(after) == tuple(before)
    assert connection.execute(
        "SELECT login FROM mt5_accounts WHERE id=?", (account_id,)
    ).fetchone()[0] == 7906571
    assert connection.execute(
        "SELECT COUNT(*) FROM mt5_terminals"
    ).fetchone()[0] == 1


def test_associates_existing_account_without_duplicate_terminal(
    lifecycle_db, tmp_path
):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    account_id = add_account(connection, login=7906571)
    service.synchronize_account(
        terminal.id,
        "ASSOCIATE_EXISTING",
        expected_account_id=account_id,
        detected_login=7906571,
        detected_server="BridgeMarkets-MT5",
        confirmed=True,
    )
    assert connection.execute(
        "SELECT mt5_terminal_id FROM mt5_accounts WHERE id=?", (account_id,)
    ).fetchone()[0] == terminal.id
    assert connection.execute(
        "SELECT COUNT(*) FROM mt5_terminals"
    ).fetchone()[0] == 1


def test_creates_detected_account_without_exposing_password_in_audit(
    lifecycle_db, tmp_path
):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    new_account = MT5Account(
        name="Detectada",
        login=7906571,
        password="super-secret-password",
        server="BridgeMarkets-MT5",
        execution_mode="OFF",
    )
    result = service.synchronize_account(
        terminal.id,
        "CREATE_ACCOUNT",
        detected_login=7906571,
        detected_server="BridgeMarkets-MT5",
        new_account=new_account,
        confirmed=True,
    )
    assert result.success
    assert connection.execute(
        "SELECT COUNT(*) FROM mt5_accounts WHERE login=7906571"
    ).fetchone()[0] == 1
    audit = "\n".join(
        row[0] for row in connection.execute("SELECT message FROM logs")
    )
    assert "super-secret-password" not in audit


def test_blocks_delete_with_profile(lifecycle_db, tmp_path):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    connection.execute(
        "INSERT INTO profiles(name,mt5_terminal_id) VALUES('demo',?)",
        (terminal.id,),
    )
    connection.commit()
    result = service.delete(terminal.id, confirm=True)
    assert not result.success
    assert any("perfil" in item for item in result.blocking_reasons)


def test_blocks_delete_with_account(lifecycle_db, tmp_path):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    add_account(connection, terminal_id=terminal.id)
    result = service.delete(terminal.id, confirm=True)
    assert not result.success
    assert any("cuenta" in item for item in result.blocking_reasons)


def test_blocks_delete_with_operations(lifecycle_db, tmp_path):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    account_id = add_account(connection, terminal_id=terminal.id)
    connection.execute(
        "INSERT INTO operations(mt5_account_id,status) VALUES(?,'CLOSED')",
        (account_id,),
    )
    connection.commit()
    result = service.dependency_report(terminal.id)
    assert any("operación" in item for item in result.blocking_reasons)


def test_blocks_delete_global_scanner(lifecycle_db, tmp_path):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    connection.execute(
        "UPDATE settings SET value='1' "
        "WHERE key='internal.scanner.enabled'"
    )
    connection.execute(
        "UPDATE settings SET value=? "
        "WHERE key='internal.scanner.mt5_terminal_id'",
        (str(terminal.id),),
    )
    connection.commit()
    result = service.delete(terminal.id, confirm=True)
    assert any("Scanner global" in item for item in result.blocking_reasons)


def test_safe_delete_removes_only_database_record(lifecycle_db, tmp_path):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    executable = Path(terminal.executable_path)
    data_path = Path(terminal.data_path)
    result = service.delete(terminal.id, confirm=True)
    assert result.success
    assert connection.execute(
        "SELECT COUNT(*) FROM mt5_terminals"
    ).fetchone()[0] == 0
    assert executable.is_file()
    assert data_path.is_dir()


def test_delete_requires_confirmation(lifecycle_db, tmp_path):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    result = service.delete(terminal.id)
    assert not result.success
    assert connection.execute(
        "SELECT COUNT(*) FROM mt5_terminals"
    ).fetchone()[0] == 1


def test_transaction_rolls_back_if_audit_fails(lifecycle_db, tmp_path):
    connection, _, _, = lifecycle_db

    class BrokenAuditService(MT5TerminalLifecycleService):
        def _audit(self, *_args, **_kwargs):
            raise RuntimeError("audit failed")

    service = BrokenAuditService(
        connection, notifier=lambda *_args: None
    )
    terminal = terminal_fixture(tmp_path)
    with pytest.raises(RuntimeError, match="audit failed"):
        service.register(terminal)
    assert connection.execute(
        "SELECT COUNT(*) FROM mt5_terminals"
    ).fetchone()[0] == 0


def test_all_writes_emit_audit_and_runtime_notification(
    lifecycle_db, tmp_path
):
    connection, service, notifications = lifecycle_db
    terminal = terminal_fixture(tmp_path)
    service.register(terminal)
    service.update(terminal.id, {"name": "Actualizada"})
    service.set_enabled(terminal.id, False)
    events = [
        row[0]
        for row in connection.execute(
            "SELECT message FROM logs ORDER BY id"
        )
    ]
    assert any("MT5_TERMINAL_REGISTERED" in item for item in events)
    assert any("MT5_TERMINAL_UPDATED" in item for item in events)
    assert any("MT5_TERMINAL_DISABLED" in item for item in events)
    assert notifications == [
        (terminal.id, "registered"),
        (terminal.id, "updated"),
        (terminal.id, "disabled"),
    ]


def test_database_unique_constraint_remains_enforced(
    lifecycle_db, tmp_path
):
    connection, service, terminal, _ = register(lifecycle_db, tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO mt5_terminals(
                name,executable_path,role,can_trade,can_scan
            ) VALUES('Duplicate',?,'TRADING',1,0)
            """,
            (terminal.executable_path,),
        )


def test_terminal_with_both_capabilities_stays_hybrid(
    lifecycle_db, tmp_path
):
    connection, _, terminal, _ = register(lifecycle_db, tmp_path)
    row = connection.execute(
        "SELECT can_trade,can_scan FROM mt5_terminals WHERE id=?",
        (terminal.id,),
    ).fetchone()
    assert tuple(row) == (1, 1)


def test_register_can_link_explicit_expected_account(
    lifecycle_db, tmp_path
):
    connection, service, _ = lifecycle_db
    account_id = add_account(connection, login=7906571)
    terminal = terminal_fixture(tmp_path)
    service.register(terminal, expected_account_id=account_id)
    assert connection.execute(
        "SELECT mt5_terminal_id FROM mt5_accounts WHERE id=?",
        (account_id,),
    ).fetchone()[0] == terminal.id


def test_missing_data_folder_is_warning_not_silent_failure(
    lifecycle_db, tmp_path
):
    _, service, _ = lifecycle_db
    terminal = terminal_fixture(tmp_path)
    terminal.data_path = str(tmp_path / "MISSING_DATA")
    result = service.register(terminal)
    assert result.success
    assert "no existe" in result.warnings[0]


def test_running_process_blocks_delete_without_removing_files(
    lifecycle_db, tmp_path
):
    connection, _, _ = lifecycle_db
    service = MT5TerminalLifecycleService(
        connection,
        notifier=lambda *_args: None,
        process_checker=lambda process_id: process_id == 999,
    )
    terminal = terminal_fixture(tmp_path)
    service.register(terminal)
    connection.execute(
        "UPDATE mt5_terminals SET process_id=999 WHERE id=?",
        (terminal.id,),
    )
    connection.commit()
    result = service.delete(terminal.id, confirm=True)
    assert not result.success
    assert any("ejecución" in item for item in result.blocking_reasons)
    assert Path(terminal.executable_path).exists()


def test_terminal_page_refreshes_inventory_without_restart(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from dashboard.pages.mt5_terminals_page import MT5TerminalsPage

    class MemoryRepository:
        def __init__(self):
            self.items = []

        def get_all(self):
            return list(self.items)

        def get_by_id(self, terminal_id):
            return next(
                (
                    terminal
                    for terminal in self.items
                    if terminal.id == terminal_id
                ),
                None,
            )

        def _available(self):
            return True

    class EmptyAccounts:
        def get_all(self):
            return []

    repository = MemoryRepository()
    app = QApplication.instance() or QApplication([])
    page = MT5TerminalsPage(
        repository=repository,
        account_repository=EmptyAccounts(),
    )
    assert page.table.rowCount() == 0
    repository.items.append(
        MT5Terminal(
            id=5,
            name="Nueva",
            executable_path=str(tmp_path / "terminal64.exe"),
            active=False,
        )
    )
    page.refresh()
    app.processEvents()
    assert page.table.rowCount() == 1
    assert page.table.item(0, 1).text() == "Nueva"
    page.table.selectRow(0)
    app.processEvents()
    assert page.edit_button.isEnabled()
    assert not page.launch_button.isEnabled()


def test_state_sync_updates_process_without_connecting_mt5(
    lifecycle_db, tmp_path
):
    connection, _, notifications = lifecycle_db
    service = MT5TerminalLifecycleService(
        connection,
        notifier=lambda terminal_id, action: notifications.append(
            (terminal_id, action)
        ),
        process_locator=lambda _path: 10428,
    )
    terminal = terminal_fixture(tmp_path)
    service.register(terminal)
    result = service.synchronize_state(terminal.id)
    row = connection.execute(
        "SELECT process_id,process_status FROM mt5_terminals WHERE id=?",
        (terminal.id,),
    ).fetchone()
    assert tuple(row) == (10428, "RUNNING")
    assert result.payload == {
        "process_id": 10428,
        "process_status": "RUNNING",
    }
