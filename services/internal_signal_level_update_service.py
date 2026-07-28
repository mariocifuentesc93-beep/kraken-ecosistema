"""Aplica cambios INTERNAL de SL/TP a operaciones abiertas correlacionadas."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LevelUpdateOutcome:
    signal_id: int | None
    updated: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    skipped: list = field(default_factory=list)


class InternalSignalLevelUpdateService:
    def __init__(
        self, signal_repository, operation_repository, profile_repository,
        milestone_repository, executor, connection_registry, logger,
        publication_service=None,
    ):
        self.signals = signal_repository
        self.operations = operation_repository
        self.profiles = profile_repository
        self.milestones = milestone_repository
        self.executor = executor
        self.connections = connection_registry
        self.logs = logger
        self.publication = publication_service

    @staticmethod
    def _target(profile, take_profits):
        targets = list(take_profits or [])
        level = int(getattr(profile, "tp_level", 1) or 1)
        return targets[min(max(level, 1), len(targets)) - 1]

    @staticmethod
    def _valid_levels(direction, current, sl, final_tp, minimum_distance=0.0):
        if not current or not sl or not final_tp:
            return False, "Niveles incompletos o precio actual no disponible."
        direction = str(direction).upper()
        if direction == "BUY":
            valid = sl < current < final_tp
        elif direction == "SELL":
            valid = sl > current > final_tp
        else:
            return False, "Dirección inválida."
        valid = valid and abs(current - sl) >= minimum_distance
        valid = valid and abs(final_tp - current) >= minimum_distance
        return (
            (True, "")
            if valid
            else (False, "Los nuevos niveles están del lado inválido del precio.")
        )

    def apply(self, update):
        signal = self.signals.get_by_idempotency_key(update.signal_key)
        outcome = LevelUpdateOutcome(getattr(signal, "id", None))
        if signal is None:
            outcome.skipped.append("SIGNAL_NOT_PERSISTED")
            return outcome

        for operation in self.operations.get_open_by_signal(signal.id):
            profile = self.profiles.get_by_id(operation.profile_id)
            if profile is None:
                outcome.failed.append((operation.id, "PROFILE_NOT_FOUND"))
                continue
            try:
                api = self.connections.connection_for(
                    operation.mt5_account_id, None
                )
                positions = api.positions_get(ticket=operation.ticket) or []
                position = positions[0] if positions else None
                if position is None:
                    outcome.skipped.append((operation.id, "POSITION_NOT_OPEN"))
                    continue
                current = float(
                    getattr(position, "price_current", 0.0) or 0.0
                )
                final_tp = self._target(profile, update.take_profits)
                symbol_info = api.symbol_info(position.symbol)
                point = float(getattr(symbol_info, "point", 0.0) or 0.0)
                stops = max(
                    int(
                        getattr(symbol_info, "trade_stops_level", 0) or 0
                    ),
                    int(
                        getattr(symbol_info, "trade_freeze_level", 0) or 0
                    ),
                )
                valid, reason = self._valid_levels(
                    operation.direction, current, update.stop_loss, final_tp,
                    point * stops,
                )
                if not valid:
                    outcome.failed.append((operation.id, reason))
                    self._log(operation, update, "REJECTED", reason)
                    continue
                result = self.executor.modify_position(
                    ticket=operation.ticket,
                    sl=float(update.stop_loss),
                    tp=float(final_tp),
                    mt5_account_id=operation.mt5_account_id,
                )
                if result is None:
                    reason = (
                        getattr(self.executor, "last_error", "")
                        or "MT5 rechazó la modificación."
                    )
                    outcome.failed.append((operation.id, reason))
                    self._log(operation, update, "FAILED", reason)
                    continue
                operation.stop_loss = float(update.stop_loss)
                # El monitor usa take_profit como disparador TP1.
                operation.take_profit = float(update.take_profits[0])
                operation.updated_at = datetime.now()
                self.operations.update(operation)
                self.milestones.update_levels(
                    operation, update.stop_loss, update.take_profits,
                    getattr(profile, "execution_mode", "UNKNOWN"),
                )
                outcome.updated.append(operation.id)
                self._log(
                    operation, update, "APPLIED",
                    f"SL={update.stop_loss} TP={final_tp}",
                )
            except Exception as error:
                outcome.failed.append((operation.id, str(error)))
                self._log(operation, update, "FAILED", str(error))

        signal.stop_loss = float(update.stop_loss)
        signal.take_profits = list(update.take_profits)
        signal.metadata["last_level_update_at"] = (
            update.detected_at.isoformat(timespec="seconds")
        )
        signal.metadata["last_level_update_changes"] = update.changes
        self.signals.update_levels(
            signal.id, signal.stop_loss, signal.take_profits, signal.metadata
        )
        if update.changes and self.publication is not None:
            self.publication.publish_update(signal, update)
        return outcome

    def _log(self, operation, update, status, detail):
        method = self.logs.info if status == "APPLIED" else self.logs.error
        method(
            "INTERNAL_LEVEL_UPDATE",
            (
                f"{status} | signal={update.signal_key} "
                f"| operation_id={operation.id} | ticket={operation.ticket} "
                f"| account_id={operation.mt5_account_id} | {detail}"
            ),
        )
