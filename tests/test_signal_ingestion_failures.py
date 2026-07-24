from copy import deepcopy

from models.signal import Signal
from services.signal_ingestion_service import SignalIngestionService


class RecordingSignalEngine:
    def __init__(self, error=None, result=True):
        self.calls = []
        self.error = error
        self.result = result

    def process(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


class FailingRepository:
    def create(self, signal):
        raise RuntimeError("database unavailable")


class FakeLogger:
    def __init__(self):
        self.entries = []

    def info(self, message, *args):
        self.entries.append(("info", message, args))

    def warning(self, message, *args):
        self.entries.append(("warning", message, args))

    def error(self, message, *args):
        self.entries.append(("error", message, args))

    def exception(self, message, *args):
        self.entries.append(("exception", message, args))


def test_invalid_identity_is_not_persisted_or_routed(
    temporary_signal_repository,
):
    engine = RecordingSignalEngine()
    service = SignalIngestionService(
        repository=temporary_signal_repository,
        signal_engine_instance=engine,
    )
    invalid = Signal(
        source="TELEGRAM",
        telegram_account_id=None,
        chat_id=-100,
        message_id=1,
    )

    result = service.ingest(invalid)

    assert result.accepted is False
    assert result.created is False
    assert result.routed is False
    assert result.error is not None
    assert temporary_signal_repository.count() == 0
    assert engine.calls == []


def test_repository_failure_never_routes():
    engine = RecordingSignalEngine()
    logger = FakeLogger()
    service = SignalIngestionService(
        repository=FailingRepository(),
        signal_engine_instance=engine,
        logger=logger,
    )
    signal = Signal(
        source="INTERNAL",
        external_signal_id="123",
        symbol="EmasVol20",
    )

    result = service.ingest(signal)

    assert result.accepted is False
    assert result.created is False
    assert result.routed is False
    assert "database unavailable" in result.error
    assert engine.calls == []
    assert logger.entries


def test_routing_failure_persists_failed_row_and_retry_is_duplicate(
    valid_signal,
    temporary_signal_repository,
):
    engine = RecordingSignalEngine(error=RuntimeError("routing failed"))
    service = SignalIngestionService(
        repository=temporary_signal_repository,
        signal_engine_instance=engine,
        logger=FakeLogger(),
    )

    first = service.ingest(valid_signal)
    second = service.ingest(deepcopy(valid_signal))

    assert first.created is True
    assert first.accepted is False
    assert first.routed is False
    assert first.signal.status == "FAILED"
    assert temporary_signal_repository.count() == 1
    assert temporary_signal_repository.get_by_id(first.signal.id).status == (
        "FAILED"
    )
    assert second.duplicate is True
    assert second.signal.status == "FAILED"
    assert len(engine.calls) == 1


def test_false_routing_result_is_reported_as_failure(
    valid_signal,
    temporary_signal_repository,
):
    service = SignalIngestionService(
        repository=temporary_signal_repository,
        signal_engine_instance=RecordingSignalEngine(result=False),
    )

    result = service.ingest(valid_signal)

    assert result.created is True
    assert result.accepted is False
    assert result.routed is False
    assert result.signal.status == "FAILED"
