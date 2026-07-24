from core.config_service import get_execution_mode
from core.signal_parser import parse_signal
from core.signal_validator import validate_signal
from repositories.signal_repository import signal_repository


def _score(signal, valid):
    if not valid:
        return 0.0
    return 40.0 + (25.0 if signal.stop_loss > 0 else 0) + (
        25.0 if signal.take_profits else 0
    ) + (10.0 if signal.rr_tp1 >= 1 else 0)


def _trade_request(signal, mode):
    return {
        "action": "SIMULATED_REQUEST", "symbol": signal.symbol,
        "direction": signal.direction, "entry": signal.entry,
        "stop_loss": signal.stop_loss, "take_profit": signal.tp1,
        "execution_mode": mode,
    }


def process_signal_message(text, chat_id=None, account_id=None, profile=None, source="Telegram"):
    """Persist signal decisions without sending an MT5 order."""
    signal = parse_signal(text)
    signal.source = source
    signal.chat_id = chat_id
    signal.telegram_account_id = account_id
    if profile is not None:
        signal.profile_id = profile.id
        signal.profile_name = profile.name

    valid, errors = validate_signal(signal)
    if signal_repository.is_duplicate(signal.raw_message, chat_id):
        errors.append("Señal duplicada")
    signal.score = _score(signal, valid and not errors)
    minimum_score = float(getattr(profile, "min_signal_score", 0) or 0)
    if not errors and minimum_score and signal.score < minimum_score:
        errors.append(
            f"Puntaje insuficiente ({signal.score:.0f}/100; mínimo {minimum_score:.0f})"
        )
    signal.metadata["parsed_fields"] = {
        "symbol": signal.symbol, "direction": signal.direction,
        "entry": signal.entry, "stop_loss": signal.stop_loss,
        "take_profits": signal.take_profits,
    }

    if errors:
        signal.status = "REJECTED"
        signal.rejection_reason = "; ".join(errors)
        signal.execution_decision = "REJECTED"
    else:
        mode = getattr(profile, "execution_mode", None) or get_execution_mode()
        signal.metadata["trade_request"] = _trade_request(signal, mode)
        if mode == "OFF":
            signal.status = "REJECTED"
            signal.rejection_reason = "Modo de ejecución OFF"
            signal.execution_decision = "REJECTED"
        elif mode == "SIMULATION":
            signal.status = "SIMULATED"
            signal.execution_decision = "SIMULATED"
        else:
            signal.status = "ACCEPTED"
            signal.execution_decision = "PENDING_MANUAL_APPROVAL"
    return signal_repository.create(signal)
