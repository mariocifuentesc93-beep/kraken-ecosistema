"""Formateo puro y envío inyectable de señales INTERNAL."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import inspect
import logging
import traceback


def format_signal_price(value):
    try:
        number = Decimal(str(value)).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ValueError(f"Precio inválido: {value!r}") from error
    integer, decimals = format(number, ".4f").split(".")
    decimals = decimals.rstrip("0")
    decimals = decimals.ljust(2, "0")
    return f"{integer}.{decimals}"


def format_internal_telegram_signal(signal):
    if str(getattr(signal, "source", "")).strip().upper() != "INTERNAL":
        raise ValueError("Solo se pueden formatear señales INTERNAL.")
    targets = list(getattr(signal, "take_profits", []))
    if len(targets) < 3:
        raise ValueError("La señal INTERNAL requiere TP1, TP2 y TP3.")
    signal_id = str(
        getattr(signal, "external_signal_id", "") or ""
    ).strip()
    if not signal_id:
        raise ValueError("external_signal_id es obligatorio.")
    direction = str(getattr(signal, "direction", "")).strip().upper()
    symbol = str(getattr(signal, "symbol", "")).strip()
    return (
        f"SIGNAL - {symbol} ({direction})\n\n"
        f"Entry: {format_signal_price(signal.entry)}\n"
        f"SL: {format_signal_price(signal.stop_loss)}\n"
        f"TP1: {format_signal_price(targets[0])}\n"
        f"TP2: {format_signal_price(targets[1])}\n"
        f"TP3: {format_signal_price(targets[2])}\n\n"
        f"Signal ID: {signal_id}"
    )


def format_internal_level_update(signal, update):
    lines = [
        f"SIGNAL UPDATE - {signal.symbol} ({signal.direction})",
        "",
    ]
    for name, (previous, current) in update.changes.items():
        lines.append(
            f"{name}: {format_signal_price(previous)} -> "
            f"{format_signal_price(current)}"
        )
    lines.extend(["", f"Signal ID: {signal.external_signal_id}"])
    return "\n".join(lines)


@dataclass(frozen=True)
class TelegramPublishResult:
    success: bool
    telegram_account_id: int
    chat_id: int
    error: str | None = None
    message_id: int | None = None
    traceback: str | None = None


class TelegramSignalPublisher:
    def __init__(self, client_provider, logger=None):
        self._client_provider = client_provider
        self._logger = logger or logging.getLogger(__name__)

    def publish(self, signal, telegram_account_id, chat_id):
        return self.publish_text(
            format_internal_telegram_signal(signal),
            telegram_account_id,
            chat_id,
            reference=signal.idempotency_key,
        )

    def publish_text(
        self, text, telegram_account_id, chat_id, reference="INTERNAL_UPDATE"
    ):
        try:
            client = self._client_provider(telegram_account_id)
            if client is None:
                raise RuntimeError("Cliente Telegram de salida no disponible.")
            result = client.send_message(
                chat_id,
                text,
            )
            if inspect.isawaitable(result):
                raise RuntimeError(
                    "El cliente asíncrono requiere un adaptador inyectado."
                )
            message_id = getattr(
                result,
                "id",
                getattr(result, "message_id", None),
            )
            if isinstance(result, dict):
                message_id = result.get("id", result.get("message_id"))
            self._logger.info(
                "Señal %s publicada en Telegram %s:%s.",
                reference,
                telegram_account_id,
                chat_id,
            )
            return TelegramPublishResult(
                True,
                telegram_account_id,
                chat_id,
                message_id=message_id,
            )
        except Exception as error:
            error_traceback = traceback.format_exc()
            self._logger.error(
                "Falló la publicación Telegram %s:%s: %s",
                telegram_account_id,
                chat_id,
                f"{error}\n{error_traceback}",
            )
            return TelegramPublishResult(
                False,
                telegram_account_id,
                chat_id,
                str(error),
                traceback=error_traceback,
            )
