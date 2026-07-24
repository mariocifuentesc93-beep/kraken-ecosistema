from pathlib import Path

from internal.checkpoint_store import InternalCheckpointStore
from internal.source import InternalSignalSource
from engine.execution_engine import ExecutionEngine
from engine.profile_engine import ProfileEngine
from engine.signal_engine import SignalEngine
from services.signal_ingestion_service import SignalIngestionService


FIXTURES = Path(__file__).parent / "fixtures" / "internal_csv"
PATTERN = "Kraken_BMSP_buy_complete.csv"


class RecordingSignalEngine:
    def __init__(self, result=True):
        self.calls = []
        self.result = result

    def process(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class FailingRepository:
    def __init__(self):
        self.calls = 0

    def create(self, signal):
        self.calls += 1
        raise RuntimeError("temporary database failure")


class FakeTradeManager:
    def __init__(self):
        self.calls = []

    def reload(self):
        return None

    def process_signal(self, signal, profile, account):
        self.calls.append((signal, profile, account))
        return True


def source(checkpoint, service):
    return InternalSignalSource(
        directory=FIXTURES,
        pattern=PATTERN,
        checkpoint_store=checkpoint,
        observation_only=False,
        ingestion_service=service,
    )


def test_new_internal_is_persisted_routed_and_checkpointed_once(
    tmp_path,
    temporary_signal_repository,
):
    engine = RecordingSignalEngine()
    service = SignalIngestionService(
        repository=temporary_signal_repository,
        signal_engine_instance=engine,
    )
    checkpoint = InternalCheckpointStore(tmp_path / "checkpoint.json")
    internal = source(checkpoint, service)

    results = internal.scan_once()

    assert len(results) == 1
    assert results[0].created is True
    assert results[0].routed is True
    assert temporary_signal_repository.count() == 1
    assert len(engine.calls) == 1
    assert checkpoint.contains("EMASVOL20", "12304") is True
    assert internal.scan_once() == []
    assert len(engine.calls) == 1


def test_duplicate_internal_is_not_routed_and_is_checkpointed(
    tmp_path,
    temporary_signal_repository,
):
    checkpoint = InternalCheckpointStore(tmp_path / "checkpoint.json")
    internal = InternalSignalSource(
        directory=FIXTURES,
        pattern=PATTERN,
    )
    existing = internal.scan_once()[0]
    temporary_signal_repository.create(existing)
    engine = RecordingSignalEngine()
    active = source(
        checkpoint,
        SignalIngestionService(
            repository=temporary_signal_repository,
            signal_engine_instance=engine,
        ),
    )

    result = active.scan_once()[0]

    assert result.duplicate is True
    assert engine.calls == []
    assert checkpoint.contains("EMASVOL20", "12304") is True


def test_persistence_failure_does_not_mark_checkpoint(tmp_path):
    checkpoint = InternalCheckpointStore(tmp_path / "checkpoint.json")
    repository = FailingRepository()
    internal = source(
        checkpoint,
        SignalIngestionService(
            repository=repository,
            signal_engine_instance=RecordingSignalEngine(),
        ),
    )

    first = internal.scan_once()
    second = internal.scan_once()

    assert len(first) == len(second) == 1
    assert first[0].created is False
    assert checkpoint.contains("EMASVOL20", "12304") is False
    assert repository.calls == 2


def test_routing_failure_is_failed_and_checkpointed(
    tmp_path,
    temporary_signal_repository,
):
    checkpoint = InternalCheckpointStore(tmp_path / "checkpoint.json")
    internal = source(
        checkpoint,
        SignalIngestionService(
            repository=temporary_signal_repository,
            signal_engine_instance=RecordingSignalEngine(result=False),
        ),
    )

    result = internal.scan_once()[0]

    assert result.created is True
    assert result.routed is False
    assert result.signal.status == "FAILED"
    assert checkpoint.contains("EMASVOL20", "12304") is True


def test_internal_simulation_runs_controlled_full_pipeline(
    tmp_path,
    temporary_signal_repository,
    profile_factory,
    account_factory,
):
    profile = profile_factory(
        1,
        signal_source_mode="INTERNAL",
        execution_mode="SIMULATION",
    )
    account = account_factory(1)
    manager = FakeTradeManager()
    execution = ExecutionEngine(manager)
    execution.start()
    profile_engine = ProfileEngine(
        accounts_provider=lambda profile_id: [account],
        execution_engine_instance=execution,
    )
    signal_engine = SignalEngine(
        profiles_provider=lambda chat_id: [],
        internal_profiles_provider=lambda: [profile],
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    signal_engine.start()
    service = SignalIngestionService(
        repository=temporary_signal_repository,
        signal_engine_instance=signal_engine,
    )
    internal = source(
        InternalCheckpointStore(tmp_path / "checkpoint.json"),
        service,
    )

    result = internal.scan_once()[0]

    assert result.accepted is True
    assert result.routed is True
    assert len(manager.calls) == 1
    signal, received_profile, received_account = manager.calls[0]
    assert signal.source == "INTERNAL"
    assert signal.execution_mode == "SIMULATION"
    assert received_profile is profile
    assert received_account is account
