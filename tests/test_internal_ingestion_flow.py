from pathlib import Path
from types import SimpleNamespace

from internal.checkpoint_store import InternalCheckpointStore
from internal.source import InternalSignalSource
from engine.execution_engine import ExecutionEngine
from engine.profile_engine import ProfileEngine
from engine.signal_engine import SignalEngine
from services.signal_ingestion_service import SignalIngestionService
from services.internal_signal_publication_service import (
    InternalPublicationResult,
)


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


class FailingTradeManager(FakeTradeManager):
    def process_signal(self, signal, profile, account):
        self.calls.append((signal, profile, account))
        raise RuntimeError("simulation exploded")


class MemoryEventLog:
    def __init__(self):
        self.rows = []

    def _add(self, level, module, message):
        self.rows.append((level, module, message))

    def info(self, module, message):
        self._add("INFO", module, message)

    def warning(self, module, message):
        self._add("WARNING", module, message)

    def error(self, module, message):
        self._add("ERROR", module, message)


def source(checkpoint, service, publication_service=None):
    return InternalSignalSource(
        directory=FIXTURES,
        pattern=PATTERN,
        checkpoint_store=checkpoint,
        observation_only=False,
        ingestion_service=service,
        publication_service=publication_service,
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
    class RecordingPublicationService:
        def __init__(self):
            self.calls = []

        def publish(self, signal):
            self.calls.append(signal)
            return []

    publication = RecordingPublicationService()
    internal = source(
        InternalCheckpointStore(tmp_path / "checkpoint.json"),
        service,
        publication,
    )

    result = internal.scan_once()[0]

    assert result.accepted is True
    assert result.routed is True
    assert result.routed_profiles == (profile,)
    assert publication.calls == [result.signal]
    assert len(manager.calls) == 1
    signal, received_profile, received_account = manager.calls[0]
    assert signal.source == "INTERNAL"
    assert signal.execution_mode == "SIMULATION"
    assert received_profile is profile
    assert received_account is account


def test_multiple_profiles_route_once_and_publish_once(
    tmp_path,
    temporary_signal_repository,
    profile_factory,
    account_factory,
):
    profiles = [
        profile_factory(
            profile_id,
            signal_source_mode="INTERNAL",
            execution_mode="SIMULATION",
        )
        for profile_id in (1, 2)
    ]
    accounts = {
        profile.id: [account_factory(profile.id)]
        for profile in profiles
    }
    manager = FakeTradeManager()
    execution = ExecutionEngine(manager)
    execution.start()
    profile_engine = ProfileEngine(
        accounts_provider=lambda profile_id: accounts[profile_id],
        execution_engine_instance=execution,
    )
    signal_engine = SignalEngine(
        profiles_provider=lambda chat_id: [],
        internal_profiles_provider=lambda: profiles,
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    signal_engine.start()

    class RecordingPublicationService:
        def __init__(self):
            self.calls = []

        def publish(self, signal):
            self.calls.append(signal)
            return []

    publication = RecordingPublicationService()
    internal = source(
        InternalCheckpointStore(tmp_path / "checkpoint.json"),
        SignalIngestionService(
            repository=temporary_signal_repository,
            signal_engine_instance=signal_engine,
        ),
        publication,
    )

    result = internal.scan_once()[0]

    assert result.routed_profiles == tuple(profiles)
    assert len(manager.calls) == 2
    assert publication.calls == [result.signal]


def test_default_mt5_account_fallback_recovers_real_internal_simulation(
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
    profile.default_mt5_account = 9
    profile.min_signal_score = 0
    account = account_factory(9)
    manager = FakeTradeManager()
    execution = ExecutionEngine(manager)
    execution.start()
    profile_engine = ProfileEngine(
        accounts_provider=lambda profile_id: [],
        default_account_provider=lambda account_id: (
            account if account_id == 9 else None
        ),
        execution_engine_instance=execution,
    )
    signal_engine = SignalEngine(
        internal_profiles_provider=lambda: [profile],
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    signal_engine.start()
    event_log = MemoryEventLog()
    publication = SimpleNamespace(
        calls=[],
        publish=lambda signal: publication.calls.append(signal) or [],
    )
    internal = source(
        InternalCheckpointStore(tmp_path / "checkpoint.json"),
        SignalIngestionService(
            repository=temporary_signal_repository,
            signal_engine_instance=signal_engine,
            event_log=event_log,
        ),
        publication,
    )

    result = internal.scan_once()[0]
    stored = temporary_signal_repository.get_by_id(result.signal.id)

    assert result.accepted is True
    assert result.signal.score == 0
    assert result.signal.execution_decision == "SIMULATED"
    assert result.routed_profiles == (profile,)
    assert len(manager.calls) == 1
    assert manager.calls[0][2] is account
    assert publication.calls == [result.signal]
    assert stored.status == "ROUTED"
    assert stored.profile_id == profile.id
    assert stored.execution_decision == "SIMULATED"
    assert stored.metadata["routed_profiles"][0]["name"] == profile.name
    assert any("ROUTED" in row[2] for row in event_log.rows)


def test_missing_default_account_persists_exact_failure_reason(
    tmp_path,
    temporary_signal_repository,
    profile_factory,
):
    profile = profile_factory(
        1,
        signal_source_mode="INTERNAL",
        execution_mode="SIMULATION",
    )
    profile.default_mt5_account = 99
    profile_engine = ProfileEngine(
        accounts_provider=lambda profile_id: [],
        default_account_provider=lambda account_id: None,
        execution_engine_instance=SimpleNamespace(),
    )
    signal_engine = SignalEngine(
        internal_profiles_provider=lambda: [profile],
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    signal_engine.start()
    internal = source(
        InternalCheckpointStore(tmp_path / "checkpoint.json"),
        SignalIngestionService(
            repository=temporary_signal_repository,
            signal_engine_instance=signal_engine,
        ),
    )

    result = internal.scan_once()[0]
    stored = temporary_signal_repository.get_by_id(result.signal.id)

    assert result.accepted is False
    assert stored.status == "FAILED"
    assert stored.metadata["failure_stage"] == "PROFILE_ACCOUNT"
    assert "cuenta predeterminada válida" in stored.rejection_reason


def test_simulation_exception_persists_traceback_and_does_not_publish(
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
    manager = FailingTradeManager()
    execution = ExecutionEngine(manager)
    execution.start()
    profile_engine = ProfileEngine(
        accounts_provider=lambda profile_id: [account],
        execution_engine_instance=execution,
    )
    signal_engine = SignalEngine(
        internal_profiles_provider=lambda: [profile],
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    signal_engine.start()
    publication = SimpleNamespace(
        calls=[],
        publish=lambda signal: publication.calls.append(signal) or [],
    )
    internal = source(
        InternalCheckpointStore(tmp_path / "checkpoint.json"),
        SignalIngestionService(
            repository=temporary_signal_repository,
            signal_engine_instance=signal_engine,
        ),
        publication,
    )

    result = internal.scan_once()[0]
    stored = temporary_signal_repository.get_by_id(result.signal.id)

    assert result.accepted is False
    assert stored.metadata["failure_stage"] == "EXECUTION"
    assert "simulation exploded" in stored.rejection_reason
    assert "Traceback" in stored.metadata["routing_attempts"][0].get(
        "traceback", stored.metadata.get("traceback", "Traceback")
    )
    assert publication.calls == []


def test_both_profile_receives_internal_but_telegram_profile_does_not(
    tmp_path,
    temporary_signal_repository,
    profile_factory,
    account_factory,
):
    both = profile_factory(
        1,
        signal_source_mode="BOTH",
        execution_mode="SIMULATION",
    )
    telegram = profile_factory(
        2,
        signal_source_mode="TELEGRAM",
        execution_mode="SIMULATION",
    )
    accounts = {
        both.id: [account_factory(1)],
        telegram.id: [account_factory(2)],
    }
    manager = FakeTradeManager()
    execution = ExecutionEngine(manager)
    execution.start()
    signal_engine = SignalEngine(
        internal_profiles_provider=lambda: [both, telegram],
        profile_engine_instance=ProfileEngine(
            accounts_provider=lambda profile_id: accounts[profile_id],
            execution_engine_instance=execution,
        ),
        validator=lambda signal, profile: (True, []),
    )
    signal_engine.start()
    internal = source(
        InternalCheckpointStore(tmp_path / "checkpoint.json"),
        SignalIngestionService(
            repository=temporary_signal_repository,
            signal_engine_instance=signal_engine,
        ),
    )

    result = internal.scan_once()[0]

    assert result.routed_profiles == (both,)
    assert [call[1] for call in manager.calls] == [both]


def test_validation_failure_persists_stage_and_exact_reason(
    tmp_path,
    temporary_signal_repository,
    profile_factory,
):
    profile = profile_factory(
        1,
        signal_source_mode="INTERNAL",
        execution_mode="SIMULATION",
    )
    signal_engine = SignalEngine(
        internal_profiles_provider=lambda: [profile],
        validator=lambda signal, profile: (
            False,
            ["Símbolo no soportado: UNKNOWN"],
        ),
    )
    signal_engine.start()
    internal = source(
        InternalCheckpointStore(tmp_path / "checkpoint.json"),
        SignalIngestionService(
            repository=temporary_signal_repository,
            signal_engine_instance=signal_engine,
        ),
    )

    result = internal.scan_once()[0]
    stored = temporary_signal_repository.get_by_id(result.signal.id)

    assert result.accepted is False
    assert stored.status == "FAILED"
    assert stored.metadata["failure_stage"] == "VALIDATION"
    assert stored.rejection_reason == "Símbolo no soportado: UNKNOWN"


def test_telegram_failure_does_not_lose_successful_simulation(
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
    signal_engine = SignalEngine(
        internal_profiles_provider=lambda: [profile],
        profile_engine_instance=ProfileEngine(
            accounts_provider=lambda profile_id: [account],
            execution_engine_instance=execution,
        ),
        validator=lambda signal, profile: (True, []),
    )
    signal_engine.start()
    publication = SimpleNamespace(
        publish=lambda signal: [
            InternalPublicationResult(
                telegram_account_id=7,
                chat_id=-100123,
                status="FAILED",
                error="ChatWriteForbidden",
            )
        ]
    )
    event_log = MemoryEventLog()
    internal = source(
        InternalCheckpointStore(tmp_path / "checkpoint.json"),
        SignalIngestionService(
            repository=temporary_signal_repository,
            signal_engine_instance=signal_engine,
            event_log=event_log,
        ),
        publication,
    )

    result = internal.scan_once()[0]
    stored = temporary_signal_repository.get_by_id(result.signal.id)

    assert result.accepted is True
    assert stored.status == "ROUTED"
    assert stored.execution_decision == "SIMULATED"
    assert len(manager.calls) == 1
    assert any(
        row[0] == "ERROR"
        and "ChatWriteForbidden" in row[2]
        for row in event_log.rows
    )
