"""Filtro puro de perfiles según la fuente de la señal."""

from core.signal_sources import (
    SignalSourceMode,
    accepts_signal_source,
    source_mode_from_operation_mode,
)


class ProfileSourceRouter:
    def mode_for(self, profile) -> str:
        value = getattr(profile, "signal_source_mode", None)
        if value is None:
            operation_mode = getattr(profile, "operation_mode", "telegram")
            return source_mode_from_operation_mode(operation_mode)
        return (
            value.value
            if isinstance(value, SignalSourceMode)
            else str(value).strip().upper()
        )

    def accepts(self, profile, signal) -> bool:
        try:
            return accepts_signal_source(
                self.mode_for(profile),
                getattr(signal, "source", None),
            )
        except ValueError:
            return False

    def filter(self, profiles, signal):
        return [
            profile
            for profile in profiles
            if self.accepts(profile, signal)
        ]


profile_source_router = ProfileSourceRouter()
