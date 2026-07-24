from models.signal import Signal
from services.signal_ingestion_service import SignalIngestionService


class RecordingSignalEngine:
    def __init__(self, result=True):
        self.calls = []
        self.result = result

    def process(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_new_telegram_signal_is_persisted_and_routed_once(
    valid_signal,
    temporary_signal_repository,
):
    engine = RecordingSignalEngine()
    service = SignalIngestionService(
        repository=temporary_signal_repository,
        signal_engine_instance=engine,
    )

    result = service.ingest(
        valid_signal,
        chat_id=-100123,
        account_id=7,
    )

    assert result.accepted is True
    assert result.created is True
    assert result.duplicate is False
    assert result.routed is True
    assert result.signal.status == "ROUTED"
    assert temporary_signal_repository.count() == 1
    assert len(engine.calls) == 1


def test_manual_internal_signal_uses_common_ingestion_service(
    temporary_signal_repository,
):
    engine = RecordingSignalEngine()
    service = SignalIngestionService(
        repository=temporary_signal_repository,
        signal_engine_instance=engine,
    )
    signal = Signal(
        source="INTERNAL",
        external_signal_id="BMSP-12241",
        symbol="LionX75",
        direction="SELL",
        entry=202870.0,
        stop_loss=203000.0,
        take_profits=[202787.66, 202700.0, 202600.0],
    )

    result = service.ingest(signal)

    assert result.accepted is True
    assert result.created is True
    assert result.signal.source == "INTERNAL"
    assert result.signal.idempotency_key == "INTERNAL:BMSP-12241"
    assert len(engine.calls) == 1
    assert temporary_signal_repository.count() == 1
