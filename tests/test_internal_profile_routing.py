from models.signal import Signal
from engine.signal_engine import SignalEngine


class RecordingProfileEngine:
    def __init__(self):
        self.calls = []

    def process_signal(self, signal, profile):
        self.calls.append((signal, profile))
        return True


def internal_signal(symbol="EmasVol20"):
    return Signal(
        source="INTERNAL",
        external_signal_id="12304",
        symbol=symbol,
        direction="BUY",
        entry=100,
        stop_loss=90,
        take_profits=[110],
    )


def test_internal_profiles_are_obtained_without_fake_chat_id(
    profile_factory,
):
    profile = profile_factory(
        1,
        signal_source_mode="INTERNAL",
    )
    internal_calls = []
    telegram_calls = []
    profile_engine = RecordingProfileEngine()
    engine = SignalEngine(
        profiles_provider=lambda chat_id: telegram_calls.append(chat_id),
        internal_profiles_provider=lambda: (
            internal_calls.append(True) or [profile]
        ),
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    engine.start()

    assert engine.process(internal_signal(), chat_id=None) is True
    assert internal_calls == [True]
    assert telegram_calls == []
    assert len(profile_engine.calls) == 1


def test_telegram_keeps_channel_lookup_and_source_filter(
    valid_signal,
    profile_factory,
):
    accepted = profile_factory(1, signal_source_mode="TELEGRAM")
    rejected = profile_factory(2, signal_source_mode="INTERNAL")
    provider_calls = []
    profile_engine = RecordingProfileEngine()
    engine = SignalEngine(
        profiles_provider=lambda chat_id: (
            provider_calls.append(chat_id) or [accepted, rejected]
        ),
        internal_profiles_provider=lambda: [],
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    engine.start()

    assert engine.process(valid_signal, chat_id=-100123) is True
    assert provider_calls == [-100123]
    assert [call[1] for call in profile_engine.calls] == [accepted]


def test_internal_symbol_filter_runs_for_each_target_profile(
    profile_factory,
):
    allowed = profile_factory(1, signal_source_mode="INTERNAL")
    blocked = profile_factory(2, signal_source_mode="BOTH")
    profile_engine = RecordingProfileEngine()

    def validator(signal, profile):
        enabled = {
            allowed.id: {"EMASVOL20"},
            blocked.id: {"LIONX75"},
        }[profile.id]
        return (
            signal.symbol.upper() in enabled,
            [] if signal.symbol.upper() in enabled else ["disabled"],
        )

    engine = SignalEngine(
        internal_profiles_provider=lambda: [allowed, blocked],
        profile_engine_instance=profile_engine,
        validator=validator,
    )
    engine.start()

    assert engine.process(internal_signal(), chat_id=None) is True
    assert [call[1] for call in profile_engine.calls] == [allowed]
