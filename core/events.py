from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


# ==========================================================
# BASE
# ==========================================================

@dataclass(slots=True)
class Event:

    timestamp: datetime = field(
        default_factory=datetime.now,
        init=False,
    )

# ==========================================================
# APPLICATION
# ==========================================================

@dataclass(slots=True)
class ApplicationStartedEvent(Event):
    pass


@dataclass(slots=True)
class ApplicationStoppedEvent(Event):
    pass


# ==========================================================
# TELEGRAM
# ==========================================================

@dataclass(slots=True)
class TelegramConnectedEvent(Event):

    account: Any


@dataclass(slots=True)
class TelegramDisconnectedEvent(Event):

    account: Any


# ==========================================================
# MT5
# ==========================================================

@dataclass(slots=True)
class MT5ConnectedEvent(Event):

    account: Any


@dataclass(slots=True)
class MT5DisconnectedEvent(Event):

    account: Any


# ==========================================================
# SIGNAL
# ==========================================================

@dataclass(slots=True)
class SignalReceivedEvent(Event):

    signal: Any

    chat_id: Optional[int] = None

    telegram_account_id: Optional[int] = None


@dataclass(slots=True)
class SignalValidatedEvent(Event):

    signal: Any


@dataclass(slots=True)
class SignalRejectedEvent(Event):

    signal: Any

    reason: str


@dataclass(slots=True)
class SignalProcessedEvent(Event):

    signal: Any


# ==========================================================
# PROFILE
# ==========================================================

@dataclass(slots=True)
class ProfileStartedEvent(Event):

    profile: Any

    signal: Any


@dataclass(slots=True)
class ProfileFinishedEvent(Event):

    profile: Any

    signal: Any

    success: bool


# ==========================================================
# EXECUTION
# ==========================================================

@dataclass(slots=True)
class ExecutionStartedEvent(Event):

    profile: Any

    account: Any

    signal: Any


@dataclass(slots=True)
class ExecutionFinishedEvent(Event):

    profile: Any

    account: Any

    signal: Any

    success: bool


@dataclass(slots=True)
class ExecutionFailedEvent(Event):

    profile: Any

    account: Any

    signal: Any

    error: str


# ==========================================================
# OPERATION
# ==========================================================

@dataclass(slots=True)
class OperationCreatedEvent(Event):

    operation: Any


@dataclass(slots=True)
class OperationOpenedEvent(Event):

    operation: Any


@dataclass(slots=True)
class OperationModifiedEvent(Event):

    operation: Any


@dataclass(slots=True)
class OperationClosedEvent(Event):

    operation: Any

    profit: float


# ==========================================================
# TP / SL
# ==========================================================

@dataclass(slots=True)
class TPReachedEvent(Event):

    operation: Any

    level: int


@dataclass(slots=True)
class StopLossEvent(Event):

    operation: Any


@dataclass(slots=True)
class BreakEvenEvent(Event):

    operation: Any


@dataclass(slots=True)
class TrailingStopEvent(Event):

    operation: Any


# ==========================================================
# RISK
# ==========================================================

@dataclass(slots=True)
class RiskRejectedEvent(Event):

    signal: Any

    reason: str


@dataclass(slots=True)
class DrawdownEvent(Event):

    value: float


@dataclass(slots=True)
class DailyLimitEvent(Event):

    value: float


@dataclass(slots=True)
class ExposureLimitEvent(Event):

    value: float


# ==========================================================
# STATISTICS
# ==========================================================

@dataclass(slots=True)
class ProfitUpdatedEvent(Event):

    profit: float


@dataclass(slots=True)
class BalanceUpdatedEvent(Event):

    balance: float


@dataclass(slots=True)
class EquityUpdatedEvent(Event):

    equity: float


@dataclass(slots=True)
class StatisticsUpdatedEvent(Event):

    statistics: Dict[str, Any]


# ==========================================================
# LOGS
# ==========================================================

@dataclass(slots=True)
class LogEvent(Event):

    message: str


@dataclass(slots=True)
class WarningEvent(Event):

    message: str


@dataclass(slots=True)
class ErrorEvent(Event):

    message: str


@dataclass(slots=True)
class NotificationEvent(Event):

    message: str