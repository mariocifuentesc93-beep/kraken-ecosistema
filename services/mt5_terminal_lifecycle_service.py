"""Transactional lifecycle rules for registered MT5 installations.

This module never opens MetaTrader and never removes files.  It only manages
Kraken's inventory and explicit account associations.
"""

from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import sqlite3

from models.mt5_account import MT5Account
from models.mt5_terminal import MT5Terminal


@dataclass(frozen=True)
class TerminalLifecycleResult:
    success: bool
    action: str
    terminal_id: int | None = None
    warnings: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    changed_fields: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)


class MT5TerminalLifecycleError(ValueError):
    """Controlled lifecycle validation error."""


class MT5TerminalLifecycleService:
    AUDIT_MODULE = "MT5TerminalLifecycle"

    def __init__(
        self,
        connection=None,
        *,
        notifier=None,
        process_checker=None,
        process_locator=None,
    ):
        self._connection = connection
        self._notifier = notifier
        self._process_checker = process_checker or self._default_process_checker
        self._process_locator = process_locator

    def _db(self):
        if self._connection is not None:
            return self._connection
        from database.database_manager import database_manager

        return database_manager.connect()

    @staticmethod
    def _default_process_checker(process_id):
        if not process_id:
            return False
        try:
            os.kill(int(process_id), 0)
            return True
        except (OSError, TypeError, ValueError):
            return False

    @staticmethod
    def _row_dict(row):
        if row is None:
            return None
        if isinstance(row, sqlite3.Row):
            return dict(row)
        if hasattr(row, "keys"):
            return {key: row[key] for key in row.keys()}
        return dict(row)

    @staticmethod
    def _normalized_path(value):
        return os.path.normcase(os.path.abspath(os.path.normpath(str(value))))

    @staticmethod
    def _role(can_trade, can_scan):
        return "TRADING" if can_trade else "SCANNER"

    @staticmethod
    def _terminal_values(terminal):
        values = {
            "name": str(terminal.name or "").strip(),
            "broker": str(terminal.broker or "").strip(),
            "executable_path": str(terminal.executable_path or "").strip(),
            "data_path": str(terminal.data_path or "").strip(),
            "catalog_id": str(
                terminal.catalog_id or "BRIDGE_SYNTHETICS"
            ).strip(),
            "can_trade": int(bool(terminal.can_trade)),
            "can_scan": int(bool(terminal.can_scan)),
            "active": int(bool(terminal.active)),
            "portable": int(bool(terminal.portable)),
            "auto_start": int(bool(terminal.auto_start)),
        }
        if not values["active"]:
            values["auto_start"] = 0
        return values

    def _validate_terminal(self, values, *, require_files=True):
        if not values["name"]:
            raise MT5TerminalLifecycleError("El nombre es obligatorio.")
        executable = Path(values["executable_path"])
        if executable.name.casefold() != "terminal64.exe":
            raise MT5TerminalLifecycleError(
                "El ejecutable debe llamarse terminal64.exe."
            )
        if require_files and not executable.is_file():
            raise MT5TerminalLifecycleError(
                f"No existe el ejecutable: {executable}"
            )
        if not values["catalog_id"]:
            raise MT5TerminalLifecycleError("El catálogo es obligatorio.")
        if not values["can_trade"] and not values["can_scan"]:
            raise MT5TerminalLifecycleError(
                "La terminal debe tener al menos una capacidad."
            )
        warnings = []
        data_path = values["data_path"]
        if data_path and not Path(data_path).is_dir():
            warnings.append(
                f"La carpeta de datos no existe actualmente: {data_path}"
            )
        return warnings

    @staticmethod
    def _columns(connection, table):
        return {
            row[1]
            for row in connection.execute(f"PRAGMA table_info({table})")
        }

    def _get_terminal_row(self, connection, terminal_id):
        row = connection.execute(
            "SELECT * FROM mt5_terminals WHERE id=?",
            (int(terminal_id),),
        ).fetchone()
        if row is None:
            raise MT5TerminalLifecycleError(
                f"No existe la terminal MT5 {terminal_id}."
            )
        return self._row_dict(row)

    def _duplicate_path(self, connection, executable_path, exclude_id=None):
        rows = connection.execute(
            "SELECT id, executable_path FROM mt5_terminals"
        ).fetchall()
        target = self._normalized_path(executable_path)
        return next(
            (
                int(row["id"])
                for row in rows
                if int(row["id"]) != int(exclude_id or -1)
                and self._normalized_path(row["executable_path"]) == target
            ),
            None,
        )

    @staticmethod
    def _begin(connection):
        if connection.in_transaction:
            connection.execute("SAVEPOINT mt5_terminal_lifecycle")
            return "savepoint"
        connection.execute("BEGIN IMMEDIATE")
        return "transaction"

    @staticmethod
    def _finish(connection, transaction_type, success):
        if transaction_type == "savepoint":
            connection.execute(
                "RELEASE SAVEPOINT mt5_terminal_lifecycle"
                if success
                else "ROLLBACK TO SAVEPOINT mt5_terminal_lifecycle"
            )
            if not success:
                connection.execute(
                    "RELEASE SAVEPOINT mt5_terminal_lifecycle"
                )
        elif success:
            connection.commit()
        else:
            connection.rollback()

    def _audit(self, connection, event, terminal, details):
        if "logs" not in {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }:
            return
        safe = dict(details or {})
        for key in tuple(safe):
            if "password" in key.casefold():
                safe.pop(key)
        message = (
            f"{event} | terminal_id={terminal.get('id')} | "
            f"nombre={terminal.get('name')} | "
            f"executable_path={terminal.get('executable_path')} | "
            f"data_path={terminal.get('data_path')} | detalles={safe}"
        )
        connection.execute(
            """
            INSERT INTO logs(level,module,message,created_at)
            VALUES(?,?,?,?)
            """,
            (
                "INFO",
                self.AUDIT_MODULE,
                message,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    def _notify(self, terminal_id, action):
        if self._notifier is not None:
            self._notifier(terminal_id, action)
            return
        from services.routing_configuration_service import (
            routing_configuration_service,
        )

        routing_configuration_service.notify_changed(
            None, f"mt5_terminal:{action}:{terminal_id}"
        )

    def register(
        self,
        terminal: MT5Terminal,
        *,
        expected_account_id=None,
        require_files=True,
    ):
        connection = self._db()
        values = self._terminal_values(terminal)
        warnings = self._validate_terminal(
            values, require_files=require_files
        )
        if self._duplicate_path(connection, values["executable_path"]):
            raise MT5TerminalLifecycleError(
                "La instalación ya está registrada."
            )
        tx = self._begin(connection)
        try:
            cursor = connection.execute(
                """
                INSERT INTO mt5_terminals(
                    name,broker,executable_path,data_path,catalog_id,role,
                    can_trade,can_scan,active,portable,auto_start
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    values["name"],
                    values["broker"],
                    values["executable_path"],
                    values["data_path"],
                    values["catalog_id"],
                    self._role(values["can_trade"], values["can_scan"]),
                    values["can_trade"],
                    values["can_scan"],
                    values["active"],
                    values["portable"],
                    values["auto_start"],
                ),
            )
            terminal_id = cursor.lastrowid
            if expected_account_id is not None:
                changed = connection.execute(
                    """
                    UPDATE mt5_accounts
                    SET mt5_terminal_id=?,terminal_path=?
                    WHERE id=?
                    """,
                    (
                        terminal_id,
                        values["executable_path"],
                        int(expected_account_id),
                    ),
                ).rowcount
                if not changed:
                    raise MT5TerminalLifecycleError(
                        "La cuenta esperada seleccionada no existe."
                    )
            persisted = self._get_terminal_row(connection, terminal_id)
            self._audit(
                connection,
                "MT5_TERMINAL_REGISTERED",
                persisted,
                {
                    "expected_account_id": expected_account_id,
                    "changed_fields": values,
                },
            )
            self._finish(connection, tx, True)
        except Exception:
            self._finish(connection, tx, False)
            raise
        terminal.id = terminal_id
        self._notify(terminal_id, "registered")
        return TerminalLifecycleResult(
            True,
            "REGISTERED",
            terminal_id,
            tuple(warnings),
            changed_fields=values,
        )

    def update(
        self,
        terminal_id,
        changes,
        *,
        allow_path_change=False,
        require_files=True,
    ):
        connection = self._db()
        before = self._get_terminal_row(connection, terminal_id)
        allowed = {
            "name", "broker", "catalog_id", "can_trade", "can_scan",
            "active", "portable", "auto_start",
        }
        path_fields = {"executable_path", "data_path"}
        supplied = dict(changes or {})
        if (
            "active" in supplied
            and int(bool(supplied["active"]))
            != int(bool(before["active"]))
        ):
            raise MT5TerminalLifecycleError(
                "Use la acción Habilitar / Deshabilitar para cambiar el estado."
            )
        unexpected = set(supplied) - allowed - path_fields
        if unexpected:
            raise MT5TerminalLifecycleError(
                f"Campos no editables: {', '.join(sorted(unexpected))}"
            )
        if set(supplied) & path_fields and not allow_path_change:
            for field_name in set(supplied) & path_fields:
                if str(supplied[field_name]) != str(before[field_name]):
                    raise MT5TerminalLifecycleError(
                        "Las rutas requieren la acción específica y confirmación."
                    )
        merged = dict(before)
        merged.update(supplied)
        values = {
            key: merged[key]
            for key in (
                "name", "broker", "executable_path", "data_path",
                "catalog_id", "can_trade", "can_scan", "active",
                "portable", "auto_start",
            )
        }
        values = self._terminal_values(MT5Terminal(**values))
        warnings = self._validate_terminal(
            values, require_files=require_files
        )
        duplicate = self._duplicate_path(
            connection, values["executable_path"], terminal_id
        )
        if duplicate:
            raise MT5TerminalLifecycleError(
                f"La ruta ya pertenece a la terminal {duplicate}."
            )
        changed = {
            key: {"before": before.get(key), "after": values[key]}
            for key in values
            if before.get(key) != values[key]
        }
        if not changed:
            return TerminalLifecycleResult(
                True, "UNCHANGED", int(terminal_id), tuple(warnings)
            )
        tx = self._begin(connection)
        try:
            connection.execute(
                """
                UPDATE mt5_terminals SET
                    name=?,broker=?,executable_path=?,data_path=?,catalog_id=?,
                    role=?,can_trade=?,can_scan=?,active=?,portable=?,
                    auto_start=?,updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    values["name"], values["broker"],
                    values["executable_path"], values["data_path"],
                    values["catalog_id"],
                    self._role(values["can_trade"], values["can_scan"]),
                    values["can_trade"], values["can_scan"],
                    values["active"], values["portable"],
                    values["auto_start"], int(terminal_id),
                ),
            )
            after = self._get_terminal_row(connection, terminal_id)
            self._audit(
                connection,
                "MT5_TERMINAL_UPDATED",
                after,
                {"changed_fields": changed},
            )
            self._finish(connection, tx, True)
        except Exception:
            self._finish(connection, tx, False)
            raise
        self._notify(terminal_id, "updated")
        return TerminalLifecycleResult(
            True,
            "UPDATED",
            int(terminal_id),
            tuple(warnings),
            changed_fields=changed,
        )

    def dependency_report(self, terminal_id):
        connection = self._db()
        terminal = self._get_terminal_row(connection, terminal_id)
        reasons = []
        profile_count = connection.execute(
            "SELECT COUNT(*) FROM profiles WHERE mt5_terminal_id=?",
            (terminal_id,),
        ).fetchone()[0]
        account_count = connection.execute(
            "SELECT COUNT(*) FROM mt5_accounts WHERE mt5_terminal_id=?",
            (terminal_id,),
        ).fetchone()[0]
        operation_count = connection.execute(
            """
            SELECT COUNT(*) FROM operations operation
            JOIN mt5_accounts account
              ON account.id=operation.mt5_account_id
            WHERE account.mt5_terminal_id=?
            """,
            (terminal_id,),
        ).fetchone()[0]
        scanner_id = connection.execute(
            "SELECT value FROM settings "
            "WHERE key='internal.scanner.mt5_terminal_id'"
        ).fetchone()
        scanner_enabled = connection.execute(
            "SELECT value FROM settings "
            "WHERE key='internal.scanner.enabled'"
        ).fetchone()
        if profile_count:
            reasons.append(f"Asociada a {profile_count} perfil(es).")
        if account_count:
            reasons.append(f"Tiene {account_count} cuenta(s) vinculada(s).")
        if operation_count:
            reasons.append(
                f"Tiene {operation_count} operación(es) relacionadas."
            )
        if (
            scanner_id
            and str(scanner_id[0]).strip() == str(terminal_id)
            and scanner_enabled
            and str(scanner_enabled[0]).lower() in {"1", "true", "yes", "on"}
        ):
            reasons.append("Es el Scanner global activo.")
        if self._process_checker(terminal.get("process_id")):
            reasons.append("El proceso de la terminal está en ejecución.")
        return TerminalLifecycleResult(
            not reasons,
            "DEPENDENCY_CHECK",
            int(terminal_id),
            blocking_reasons=tuple(reasons),
            payload={
                "profiles": profile_count,
                "accounts": account_count,
                "operations": operation_count,
            },
        )

    def set_enabled(self, terminal_id, enabled):
        connection = self._db()
        terminal = self._get_terminal_row(connection, terminal_id)
        enabled = bool(enabled)
        if not enabled:
            report = self.dependency_report(terminal_id)
            scanner_block = tuple(
                reason
                for reason in report.blocking_reasons
                if "Scanner global" in reason
            )
            if scanner_block:
                self._audit(
                    connection,
                    "MT5_TERMINAL_DELETE_BLOCKED",
                    terminal,
                    {"blocking_reasons": scanner_block},
                )
                connection.commit()
                return TerminalLifecycleResult(
                    False,
                    "DISABLE_BLOCKED",
                    int(terminal_id),
                    blocking_reasons=scanner_block,
                )
        changed = {
            "active": {
                "before": int(bool(terminal["active"])),
                "after": int(enabled),
            }
        }
        tx = self._begin(connection)
        try:
            connection.execute(
                """
                UPDATE mt5_terminals
                SET active=?, auto_start=CASE WHEN ?=0 THEN 0 ELSE auto_start END,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (int(enabled), int(enabled), int(terminal_id)),
            )
            after = self._get_terminal_row(connection, terminal_id)
            event = (
                "MT5_TERMINAL_ENABLED"
                if enabled
                else "MT5_TERMINAL_DISABLED"
            )
            self._audit(connection, event, after, {"changed_fields": changed})
            self._finish(connection, tx, True)
        except Exception:
            self._finish(connection, tx, False)
            raise
        self._notify(terminal_id, "enabled" if enabled else "disabled")
        return TerminalLifecycleResult(
            True,
            "ENABLED" if enabled else "DISABLED",
            int(terminal_id),
            changed_fields=changed,
        )

    def synchronize_state(self, terminal_id):
        connection = self._db()
        terminal = self._get_terminal_row(connection, terminal_id)
        if self._process_locator is None:
            from services.mt5_process_discovery_service import (
                mt5_process_discovery_service,
            )

            process_id = mt5_process_discovery_service.find_pid(
                terminal["executable_path"]
            )
        else:
            process_id = self._process_locator(
                terminal["executable_path"]
            )
        process_status = "RUNNING" if process_id else "STOPPED"
        changed = {
            "process_id": {
                "before": terminal.get("process_id"),
                "after": process_id,
            },
            "process_status": {
                "before": terminal.get("process_status"),
                "after": process_status,
            },
        }
        tx = self._begin(connection)
        try:
            connection.execute(
                """
                UPDATE mt5_terminals SET
                    process_id=?,process_status=?,connection_status=?,
                    last_seen_at=CURRENT_TIMESTAMP,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    process_id,
                    process_status,
                    process_status,
                    int(terminal_id),
                ),
            )
            after = self._get_terminal_row(connection, terminal_id)
            self._audit(
                connection,
                "MT5_TERMINAL_UPDATED",
                after,
                {"changed_fields": changed, "read_only_process_sync": True},
            )
            self._finish(connection, tx, True)
        except Exception:
            self._finish(connection, tx, False)
            raise
        self._notify(terminal_id, "state_synchronized")
        return TerminalLifecycleResult(
            True,
            "STATE_SYNCHRONIZED",
            int(terminal_id),
            changed_fields=changed,
            payload={"process_id": process_id, "process_status": process_status},
        )

    def synchronize_account(
        self,
        terminal_id,
        strategy,
        *,
        expected_account_id=None,
        detected_login=None,
        detected_server=None,
        detected_broker=None,
        new_account=None,
        confirmed=False,
    ):
        connection = self._db()
        terminal = self._get_terminal_row(connection, terminal_id)
        strategy = str(strategy or "MAINTAIN").strip().upper()
        if strategy == "MAINTAIN":
            return TerminalLifecycleResult(
                True, "ACCOUNT_MAINTAINED", int(terminal_id)
            )
        if not confirmed:
            raise MT5TerminalLifecycleError(
                "La sincronización de cuenta requiere confirmación explícita."
            )
        tx = self._begin(connection)
        try:
            previous = None
            target_account_id = expected_account_id
            if strategy == "UPDATE_EXPECTED":
                if expected_account_id is None:
                    raise MT5TerminalLifecycleError(
                        "Seleccione la cuenta esperada que desea actualizar."
                    )
                previous_row = connection.execute(
                    """
                    SELECT login,server,mt5_terminal_id
                    FROM mt5_accounts WHERE id=?
                    """,
                    (int(expected_account_id),),
                ).fetchone()
                if previous_row is None:
                    raise MT5TerminalLifecycleError(
                        "La cuenta esperada no existe."
                    )
                previous = dict(previous_row)
                if previous["mt5_terminal_id"] != int(terminal_id):
                    raise MT5TerminalLifecycleError(
                        "La cuenta elegida no está vinculada a esta terminal. "
                        "Use Asociar una cuenta existente."
                    )
                connection.execute(
                    """
                    UPDATE mt5_accounts
                    SET login=?,server=?,terminal_path=?,mt5_terminal_id=?
                    WHERE id=?
                    """,
                    (
                        int(detected_login),
                        str(detected_server or ""),
                        terminal["executable_path"],
                        int(terminal_id),
                        int(expected_account_id),
                    ),
                )
            elif strategy == "ASSOCIATE_EXISTING":
                if expected_account_id is None:
                    raise MT5TerminalLifecycleError(
                        "Seleccione una cuenta existente."
                    )
                existing = connection.execute(
                    "SELECT login,server FROM mt5_accounts WHERE id=?",
                    (int(expected_account_id),),
                ).fetchone()
                if existing is None:
                    raise MT5TerminalLifecycleError(
                        "La cuenta seleccionada no existe."
                    )
                if (
                    detected_login not in (None, "")
                    and str(existing["login"]).strip()
                    != str(detected_login).strip()
                ):
                    raise MT5TerminalLifecycleError(
                        "La cuenta existente no coincide con el login detectado."
                    )
                if (
                    detected_server not in (None, "")
                    and str(existing["server"] or "").strip().casefold()
                    != str(detected_server).strip().casefold()
                ):
                    raise MT5TerminalLifecycleError(
                        "La cuenta existente no coincide con el servidor detectado."
                    )
                changed = connection.execute(
                    """
                    UPDATE mt5_accounts
                    SET mt5_terminal_id=?,terminal_path=?
                    WHERE id=?
                    """,
                    (
                        int(terminal_id),
                        terminal["executable_path"],
                        int(expected_account_id),
                    ),
                ).rowcount
                if not changed:
                    raise MT5TerminalLifecycleError(
                        "No se pudo asociar la cuenta seleccionada."
                    )
            elif strategy == "CREATE_ACCOUNT":
                account = new_account
                if account is None:
                    account = MT5Account(
                        name=f"MT5 {detected_login}",
                        login=int(detected_login),
                        server=str(detected_server or ""),
                    )
                cursor = connection.execute(
                    """
                    INSERT INTO mt5_accounts(
                        name,login,password,server,terminal_path,execution_mode,
                        risk_enabled,risk_mode,risk_percent,risk_amount,
                        fixed_lot,magic_number,custom_magic,comment,deviation,
                        active,auto_connect,reconnect,description,mt5_terminal_id
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        account.name,
                        int(detected_login or account.login),
                        account.password,
                        str(detected_server or account.server),
                        terminal["executable_path"],
                        account.execution_mode,
                        int(bool(account.risk_enabled)),
                        account.risk_mode,
                        account.risk_percent,
                        account.risk_amount,
                        account.fixed_lot,
                        account.magic_number,
                        account.custom_magic,
                        account.comment,
                        account.deviation,
                        int(bool(account.active)),
                        int(bool(account.auto_connect)),
                        int(bool(account.reconnect)),
                        account.description,
                        int(terminal_id),
                    ),
                )
                target_account_id = cursor.lastrowid
            else:
                raise MT5TerminalLifecycleError(
                    f"Estrategia de sincronización desconocida: {strategy}"
                )
            connection.execute(
                """
                UPDATE mt5_terminals
                SET detected_login=?,detected_server=?,
                    account_match_status='MATCH',updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    str(detected_login or ""),
                    str(detected_server or ""),
                    int(terminal_id),
                ),
            )
            after = self._get_terminal_row(connection, terminal_id)
            audit_details = {
                "strategy": strategy,
                "previous_account": previous,
                "new_account_id": target_account_id,
                "detected_login": detected_login,
                "detected_server": detected_server,
                "detected_broker": detected_broker,
            }
            self._audit(
                connection,
                "MT5_TERMINAL_ACCOUNT_SYNCED",
                after,
                audit_details,
            )
            self._finish(connection, tx, True)
        except Exception:
            self._finish(connection, tx, False)
            raise
        self._notify(terminal_id, "account_synced")
        return TerminalLifecycleResult(
            True,
            "ACCOUNT_SYNCED",
            int(terminal_id),
            changed_fields={
                "account_id": target_account_id,
                "strategy": strategy,
            },
        )

    def delete(self, terminal_id, *, confirm=False, allow_running=False):
        connection = self._db()
        terminal = self._get_terminal_row(connection, terminal_id)
        report = self.dependency_report(terminal_id)
        reasons = list(report.blocking_reasons)
        if allow_running:
            reasons = [
                reason for reason in reasons if "en ejecución" not in reason
            ]
        if reasons or not confirm:
            if not confirm:
                reasons.append("Falta confirmación explícita.")
            tx = self._begin(connection)
            try:
                self._audit(
                    connection,
                    "MT5_TERMINAL_DELETE_BLOCKED",
                    terminal,
                    {"blocking_reasons": reasons},
                )
                self._finish(connection, tx, True)
            except Exception:
                self._finish(connection, tx, False)
                raise
            return TerminalLifecycleResult(
                False,
                "DELETE_BLOCKED",
                int(terminal_id),
                blocking_reasons=tuple(reasons),
            )
        tx = self._begin(connection)
        try:
            self._audit(
                connection,
                "MT5_TERMINAL_DELETED",
                terminal,
                {"record_only": True},
            )
            connection.execute(
                "DELETE FROM mt5_terminals WHERE id=?",
                (int(terminal_id),),
            )
            self._finish(connection, tx, True)
        except Exception:
            self._finish(connection, tx, False)
            raise
        self._notify(terminal_id, "deleted")
        return TerminalLifecycleResult(
            True,
            "DELETED",
            int(terminal_id),
            warnings=(
                "Solo se eliminó el registro de Kraken; no se borraron archivos.",
            ),
        )


mt5_terminal_lifecycle_service = MT5TerminalLifecycleService()
