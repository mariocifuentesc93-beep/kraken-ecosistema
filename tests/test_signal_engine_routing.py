from core.signal_validator import validate_signal
from engine.signal_engine import SignalEngine


class RecordingProfileEngine:
    def __init__(self):
        self.calls = []

    def process_signal(self, signal, profile):
        self.calls.append((signal, profile))
        return True


def test_signal_engine_is_only_profile_router(
    valid_signal,
    profile_factory,
):
    enabled = profile_factory(1, "Enabled")
    disabled = profile_factory(2, "Disabled", enabled=False)
    provider_calls = []
    profile_engine = RecordingProfileEngine()

    def profiles_provider(chat_id):
        provider_calls.append(chat_id)
        return [enabled, disabled]

    engine = SignalEngine(
        profiles_provider=profiles_provider,
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    engine.start()

    result = engine.process(
        valid_signal,
        chat_id=-100123,
        account_id=7,
    )

    assert result is True
    assert provider_calls == [-100123]
    assert len(profile_engine.calls) == 1
    assert profile_engine.calls[0][1] is enabled


def test_validation_uses_symbols_for_the_target_profile(
    valid_signal,
    profile_factory,
):
    profile = profile_factory(5)

    valid, errors = validate_signal(
        valid_signal,
        profile=profile,
        enabled_symbols=["EmasVol20"],
    )
    assert valid is True
    assert errors == []

    valid, errors = validate_signal(
        valid_signal,
        profile=profile,
        enabled_symbols=["LionX75"],
    )
    assert valid is False
    assert any("deshabilitado" in error for error in errors)
