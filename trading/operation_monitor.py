import threading
import time
from datetime import datetime

from mt5.executor import mt5_executor
from repositories.log_repository import log_repository
from repositories.operation_repository import (
    operation_repository,
)
from repositories.profile_repository import profile_repository
from repositories.operation_milestone_repository import (
    operation_milestone_repository,
)
from database.database_manager import database_manager


class OperationMonitor:

    def __init__(
        self,
        operation_repo=None,
        profile_repo=None,
        executor=None,
        mt5_api=None,
        logs=None,
        milestone_repo=None,
        connection_registry=None,
        account_provider=None,
    ):

        self.running = False

        self.thread = None

        self.interval = 1
        self.operation_repository = operation_repo or operation_repository
        self.profile_repository = profile_repo or profile_repository
        self.executor = executor or mt5_executor
        self.mt5 = mt5_api
        self.logs = logs or log_repository
        self.milestones = milestone_repo or operation_milestone_repository
        self._connection_registry = connection_registry
        self._account_provider = account_provider

    def _account(self, account_id):
        if self._account_provider is None:
            from repositories.mt5_account_repository import (
                mt5_account_repository,
            )

            self._account_provider = mt5_account_repository.get_by_id
        return self._account_provider(account_id)

    def _api(self, account_id):
        if self.mt5 is not None:
            return self.mt5
        if self._connection_registry is None:
            from services.mt5_connection_registry import (
                mt5_connection_registry,
            )

            self._connection_registry = mt5_connection_registry
        return self._connection_registry.connection_for(
            account_id,
            None,
        )

    @staticmethod
    def _group_by_account(operations):
        grouped = {}
        for operation in operations:
            grouped.setdefault(
                getattr(operation, "mt5_account_id", None), []
            ).append(operation)
        return grouped

    # -------------------------------------------------

    def start(self):

        if self.running:

            return

        self.running = True
        self._recovery_pending = True

        self.thread = threading.Thread(

            target=self._loop,

            daemon=True,

        )

        self.thread.start()

        print(

            "[OperationMonitor] iniciado."

        )

    # -------------------------------------------------

    def stop(self):

        self.running = False

        thread = self.thread
        if thread is not None and thread is not threading.current_thread():
            thread.join()
        self.thread = None

        print(

            "[OperationMonitor] detenido."

        )

    # -------------------------------------------------

    def _loop(self):
        try:
            while self.running:
                try:
                    if getattr(self, "_recovery_pending", False):
                        self._recovery_pending = not bool(
                            self.recover_open_operations()
                        )
                    else:
                        self.update()
                except Exception as error:
                    print(f"[OperationMonitor] {error}")
                time.sleep(self.interval)
        finally:
            database_manager.close()

    # -------------------------------------------------

    def update(self):

        operations = self.operation_repository.get_open()

        if not operations:

            return

        for account_id, account_operations in self._group_by_account(
            operations
        ).items():
            try:
                api = self._api(account_id)
                positions = api.positions_get()
            except Exception as error:
                self.logs.error(
                    "OPERATION_MONITOR",
                    (
                        f"ACCOUNT_MONITOR_FAILED | account_id={account_id} "
                        f"| error={error}"
                    ),
                )
                continue
            if positions is None:
                continue
            active = {
                int(position.ticket): position for position in positions
            }
            for operation in account_operations:
                if int(operation.ticket or 0) not in active:
                    self._finalize_closed_operation(operation, api)
                    continue
                position = active[int(operation.ticket)]
                operation.profit = position.profit
                operation.swap = position.swap
                self._record_price_milestones(operation, position)
                self._protect_tp1(operation, position)
                self.operation_repository.update(operation)

    def recover_open_operations(self):
        """Reconcile persisted OPEN tickets without duplicating protection."""
        operations = self.operation_repository.get_open()
        if not operations and self.mt5 is not None:
            positions = self.mt5.positions_get()
            if positions is None:
                self.logs.error(
                    "OPERATION_MONITOR",
                    "RECOVERY_DEFERRED | MT5 no devolvió posiciones abiertas.",
                )
                return False
            self.backfill_closed_milestones()
            return True
        all_recovered = True
        for account_id, account_operations in self._group_by_account(
            operations
        ).items():
            try:
                api = self._api(account_id)
                positions = api.positions_get()
            except Exception as error:
                self.logs.error(
                    "OPERATION_MONITOR",
                    (
                        f"RECOVERY_DEFERRED | account_id={account_id} "
                        f"| error={error}"
                    ),
                )
                all_recovered = False
                continue
            if positions is None:
                all_recovered = False
                continue
            active = {
                int(position.ticket): position for position in positions
            }
            for operation in account_operations:
                position = active.get(int(operation.ticket or 0))
                if position is None:
                    self._finalize_closed_operation(operation, api)
                    continue
                operation.profit = float(
                    getattr(position, "profit", 0.0) or 0.0
                )
                operation.swap = float(
                    getattr(position, "swap", 0.0) or 0.0
                )
                self._record_price_milestones(operation, position)
                self._protect_tp1(operation, position, reconcile=True)
                self.operation_repository.update(operation)
                self.logs.info(
                    "OPERATION_MONITOR",
                    (
                        f"RECOVERED | operation_id={operation.id} "
                        f"| ticket={operation.ticket} "
                        f"| account_id={account_id} "
                        f"| symbol={operation.symbol} "
                        f"| protected={int(bool(operation.trailing_stop))}"
                    ),
                )
        self.backfill_closed_milestones()
        return all_recovered

    def backfill_closed_milestones(self):
        """Complete missing TP milestones for previously closed MT5 tickets."""
        get_closed = getattr(self.operation_repository, "get_closed", None)
        if not callable(get_closed):
            return
        for operation in get_closed():
            if not operation.ticket:
                continue
            levels = self.milestones.levels(operation)
            if not (levels.get("TP2") or levels.get("TP3")):
                continue
            reached_before = self.milestones.reached(operation.id)
            if "TP2" in reached_before or "TP3" in reached_before:
                continue
            try:
                api = self._api(
                    getattr(operation, "mt5_account_id", None)
                )
            except Exception:
                continue
            close_state = self._record_close_milestone(operation, api)
            reached_after = self.milestones.reached(operation.id)
            if reached_after == reached_before:
                continue
            operation.updated_at = datetime.now()
            if operation.profit > 0:
                operation.result = "WIN"
            elif operation.profit < 0:
                operation.result = "LOSS"
            self.operation_repository.update(operation)
            self.logs.info(
                "OPERATION_MONITOR",
                (
                    f"MILESTONES_BACKFILLED | operation_id={operation.id} "
                    f"| ticket={operation.ticket} | symbol={operation.symbol} "
                    f"| reason={close_state or 'MT5_HISTORY'} "
                    f"| reached={','.join(sorted(reached_after))}"
                ),
            )

    def _finalize_closed_operation(self, operation, api=None):
        close_state = self._record_close_milestone(
            operation,
            api or self._api(getattr(operation, "mt5_account_id", None)),
        )
        operation.status = "CLOSED"
        operation.closed_at = datetime.now()
        operation.updated_at = operation.closed_at
        if operation.profit > 0:
            operation.result = "WIN"
        elif operation.profit < 0:
            operation.result = "LOSS"
        else:
            operation.result = "BREAKEVEN"
        operation.close_reason = close_state or "MT5_CLOSED"
        self.operation_repository.update(operation)
        self.logs.info(
            "OPERATION_MONITOR",
            (
                f"POSITION_CLOSED | operation_id={operation.id} "
                f"| ticket={operation.ticket} | symbol={operation.symbol} "
                f"| reason={operation.close_reason} "
                f"| exit={operation.exit_price} | profit={operation.profit}"
            ),
        )

    def _record_price_milestones(self, operation, position):
        levels = self.milestones.levels(operation)
        reached = self.milestones.reached(operation.id)
        direction = str(operation.direction or "").upper()
        current = float(getattr(position, "price_current", 0.0) or 0.0)
        profile = self.profile_repository.get_by_id(operation.profile_id)
        mode = str(
            getattr(profile, "execution_mode", "UNKNOWN") or "UNKNOWN"
        ).upper()
        for milestone in ("TP1", "TP2", "TP3"):
            level = float(levels.get(milestone) or 0.0)
            if not level or milestone in reached:
                continue
            hit = (
                direction == "BUY" and current >= level
            ) or (
                direction == "SELL" and current <= level
            )
            if hit and self.milestones.record(
                operation, milestone, current, mode
            ):
                self.logs.info(
                    "OPERATION_MONITOR",
                    (
                        f"{milestone}_HIT | operation_id={operation.id} "
                        f"| ticket={operation.ticket} | symbol={operation.symbol} "
                        f"| level={level} | price={current}"
                    ),
                )

    def _record_close_milestone(self, operation, api=None):
        api = api or self._api(
            getattr(operation, "mt5_account_id", None)
        )
        history = getattr(api, "history_deals_get", None)
        if not callable(history):
            return ""
        position_id = operation.position_id or operation.ticket
        try:
            deals = history(position=position_id) or []
        except Exception:
            return ""
        closing = [
            deal for deal in deals
            if int(getattr(deal, "entry", -1))
            in {
                int(getattr(api, "DEAL_ENTRY_OUT", -2)),
                int(getattr(api, "DEAL_ENTRY_OUT_BY", -3)),
            }
        ]
        if not closing:
            return ""
        deal = closing[-1]
        operation.exit_price = float(getattr(deal, "price", 0.0) or 0.0)
        operation.profit = float(sum(
            float(getattr(item, "profit", 0.0) or 0.0)
            + float(getattr(item, "commission", 0.0) or 0.0)
            + float(getattr(item, "swap", 0.0) or 0.0)
            for item in deals
        ))
        profile = self.profile_repository.get_by_id(operation.profile_id)
        mode = str(
            getattr(profile, "execution_mode", "UNKNOWN") or "UNKNOWN"
        ).upper()
        levels = self.milestones.levels(operation)
        reached = self.milestones.reached(operation.id)
        direction = str(operation.direction or "").upper()
        highest = ""
        for milestone in ("TP1", "TP2", "TP3"):
            level = float(levels.get(milestone) or 0.0)
            hit = level > 0 and (
                (direction == "BUY" and operation.exit_price >= level)
                or (direction == "SELL" and operation.exit_price <= level)
            )
            if not hit:
                continue
            if milestone not in reached:
                self.milestones.record(
                    operation, milestone, operation.exit_price, mode
                )
                reached.add(milestone)
            highest = milestone

        reason = int(getattr(deal, "reason", -1))
        if reason == int(getattr(api, "DEAL_REASON_SL", -3)):
            if "TP1" not in reached:
                self.milestones.record(
                    operation, "SL", operation.exit_price, mode
                )
                return "STOP_LOSS"
            return highest or "TP1_PROTECTED"
        if highest:
            return f"{highest}_HIT"
        if reason == int(getattr(api, "DEAL_REASON_TP", -2)):
            return "TAKE_PROFIT"
        return "MT5_CLOSED"

    def _protect_tp1(self, operation, position, reconcile=False):
        """Move SL to TP1 once, while preserving the configured final TP."""
        if operation.trailing_stop and not reconcile:
            return
        profile = self.profile_repository.get_by_id(operation.profile_id)
        if profile is None:
            return
        if not bool(getattr(profile, "trailing_stop_enabled", False)):
            return
        if getattr(profile, "tp1_management", "") != "PROTECT_TP1":
            return

        tp1 = float(operation.take_profit or 0.0)
        current_price = float(getattr(position, "price_current", 0.0) or 0.0)
        if tp1 <= 0 or current_price <= 0:
            return

        direction = str(operation.direction or "").upper()
        reached = bool(operation.trailing_stop) or (
            direction == "BUY" and current_price >= tp1
        ) or (
            direction == "SELL" and current_price <= tp1
        )
        if not reached:
            return

        current_sl = float(getattr(position, "sl", 0.0) or 0.0)
        already_protected = (
            direction == "BUY" and current_sl >= tp1
        ) or (
            direction == "SELL" and current_sl > 0 and current_sl <= tp1
        )

        if not already_protected:
            final_tp = float(getattr(position, "tp", 0.0) or 0.0)
            modify_kwargs = {
                "ticket": operation.ticket,
                "sl": tp1,
                "tp": final_tp,
            }
            if getattr(operation, "mt5_account_id", None) is not None:
                modify_kwargs["mt5_account_id"] = operation.mt5_account_id
            result = self.executor.modify_position(**modify_kwargs)
            if result is None:
                self.logs.error(
                    "OPERATION_MONITOR",
                    (
                        f"TP1_PROTECTION_FAILED | operation_id={operation.id} "
                        f"| ticket={operation.ticket} | symbol={operation.symbol} "
                        f"| tp1={tp1}"
                    ),
                )
                return

        operation.stop_loss = tp1
        operation.trailing_stop = True
        if not already_protected:
            self.logs.info(
                "OPERATION_MONITOR",
                (
                    f"TP1_PROTECTED | operation_id={operation.id} "
                    f"| ticket={operation.ticket} | profile_id={operation.profile_id} "
                    f"| symbol={operation.symbol} | direction={direction} "
                    f"| sl={tp1} | final_tp={getattr(position, 'tp', 0.0)}"
                ),
            )


operation_monitor = OperationMonitor()
