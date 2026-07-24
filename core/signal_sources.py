"""Contrato de selección de fuentes automáticas por perfil."""

from enum import Enum


class SignalSourceMode(Enum):
    OFF = "OFF"
    TELEGRAM = "TELEGRAM"
    INTERNAL = "INTERNAL"
    BOTH = "BOTH"


def normalize_signal_source_mode(value) -> str:
    if isinstance(value, SignalSourceMode):
        return value.value
    normalized = str(value or "").strip().upper()
    if normalized not in {mode.value for mode in SignalSourceMode}:
        raise ValueError(
            f"Modo de fuente de señal no soportado: {value!r}"
        )
    return normalized


def source_mode_from_operation_mode(operation_mode) -> str:
    """Mapeo explícito para perfiles heredados."""
    normalized = str(operation_mode or "").strip().lower()
    return {
        "telegram": SignalSourceMode.TELEGRAM.value,
        "both": SignalSourceMode.BOTH.value,
        "manual": SignalSourceMode.OFF.value,
    }.get(normalized, SignalSourceMode.OFF.value)


def accepts_signal_source(mode, source) -> bool:
    normalized_mode = normalize_signal_source_mode(mode)
    normalized_source = str(source or "").strip().upper()
    accepted = {
        SignalSourceMode.OFF.value: set(),
        SignalSourceMode.TELEGRAM.value: {"TELEGRAM"},
        SignalSourceMode.INTERNAL.value: {"INTERNAL"},
        SignalSourceMode.BOTH.value: {"TELEGRAM", "INTERNAL"},
    }
    return normalized_source in accepted[normalized_mode]
