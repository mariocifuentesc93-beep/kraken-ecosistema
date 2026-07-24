from copy import deepcopy

from engine.signal_engine import SignalEngine
from models.signal import Signal
from services.signal_ingestion_service import SignalIngestionService


class RecordingSignalEngine:
    def __init__(self):
        self.calls = []

    def process(self, **kwargs):
        self.calls.append(kwargs)
        return True


class RecordingProfileEngine:
    def __init__(self):
        self.calls = []

    def process_signal(self, signal, profile):
        self.calls.append((signal, profile))
        return True


def test_duplicate_telegram_is_not_persisted_or_routed_again(
    valid_signal,
    temporary_signal_repository,
):
    engine = RecordingSignalEngine()
    service = SignalIngestionService(
        repository=temporary_signal_repository,
        signal_engine_instance=engine,
    )

    first = service.ingest(valid_signal)
    second = service.ingest(deepcopy(valid_signal))

    assert first.created is True
    assert second.duplicate is True
    assert second.created is False
    assert second.routed is False
    assert second.signal.id == first.signal.id
    assert second.signal.status == "ROUTED"
    assert temporary_signal_repository.count() == 1
    assert len(engine.calls) == 1


def test_duplicate_internal_is_not_routed_again(
    temporary_signal_repository,
):
    engine = RecordingSignalEngine()
    service = SignalIngestionService(
        repository=temporary_signal_repository,
        signal_engine_instance=engine,
    )

    def internal_signal():
        return Signal(
            source="INTERNAL",
            external_signal_id="12241",
            symbol="LionX75",
            direction="SELL",
            entry=100.0,
            stop_loss=110.0,
            take_profits=[90.0],
        )

    first = service.ingest(internal_signal())
    duplicate = service.ingest(internal_signal())

    assert first.created is True
    assert duplicate.duplicate is True
    assert temporary_signal_repository.count() == 1
    assert len(engine.calls) == 1


def test_multiple_profiles_receive_copies_but_signal_is_stored_once(
    valid_signal,
    temporary_signal_repository,
    profile_factory,
):
    profiles = [
        profile_factory(1, "Profile A"),
        profile_factory(2, "Profile B"),
    ]
    profile_engine = RecordingProfileEngine()
    signal_engine = SignalEngine(
        profiles_provider=lambda chat_id: profiles,
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    signal_engine.start()
    service = SignalIngestionService(
        repository=temporary_signal_repository,
        signal_engine_instance=signal_engine,
    )

    result = service.ingest(valid_signal)

    assert result.routed is True
    assert temporary_signal_repository.count() == 1
    assert len(profile_engine.calls) == 2
    first_signal = profile_engine.calls[0][0]
    second_signal = profile_engine.calls[1][0]
    assert first_signal is not second_signal
    assert first_signal.id == second_signal.id == result.signal.id
