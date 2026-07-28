from types import SimpleNamespace

from engine.signal_engine import SignalEngine
from internal.source import InternalSignalSource
from models.signal import Signal
from services.signal_ingestion_service import SignalIngestionService


class MemoryRepository:
    def __init__(self):
        self.signal = None

    def create(self, signal):
        signal.id = 1
        self.signal = signal
        return SimpleNamespace(created=True, signal=signal)

    def update_outcome(self, signal):
        self.signal = signal


class RecordingPublication:
    def __init__(self):
        self.calls = []

    def publish(self, signal):
        self.calls.append(signal.idempotency_key)
        return []


def internal_signal(external_id="9001"):
    return Signal(
        source="INTERNAL",
        external_signal_id=external_id,
        symbol="EMASVOL10",
        direction="BUY",
        entry=100.0,
        stop_loss=90.0,
        take_profits=[110.0, 120.0, 130.0],
        raw_message="fixture",
    )


def test_internal_without_profiles_is_valid_and_not_failed():
    repository = MemoryRepository()
    engine = SignalEngine(internal_profiles_provider=lambda: [])
    engine.start()
    result = SignalIngestionService(
        repository=repository,
        signal_engine_instance=engine,
        event_log=SimpleNamespace(info=lambda *args: None),
    ).ingest(internal_signal())

    assert result.accepted is True
    assert result.created is True
    assert result.routed is False
    assert result.signal.status == "RECEIVED"
    assert result.signal.metadata["routing_status"] == "NO_ELIGIBLE_PROFILES"
    assert result.signal.metadata["execution_status"] == "SKIPPED"


def test_internal_profile_provider_is_consulted_for_each_signal():
    profiles = []
    calls = []
    profile_engine = SimpleNamespace(
        process_signal=lambda signal, profile: calls.append(profile) or True
    )
    engine = SignalEngine(
        internal_profiles_provider=lambda: list(profiles),
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    engine.start()

    first = internal_signal("9002")
    assert engine.process(first, None) is False

    profile = SimpleNamespace(
        id=1,
        name="demo",
        active=True,
        enabled=True,
        signal_source_mode="INTERNAL",
        execution_mode="SIMULATION",
    )
    profiles.append(profile)
    second = internal_signal("9003")
    assert engine.process(second, None) is True
    assert calls == [profile]


def test_publication_is_independent_when_routing_has_no_profiles():
    publication = RecordingPublication()
    result = SimpleNamespace(
        created=True,
        duplicate=False,
        signal=internal_signal("9004"),
    )
    result.signal.id = 1
    ingestion = SimpleNamespace(
        ingest=lambda signal: result,
        record_event=lambda *args, **kwargs: None,
        update_outcome=lambda signal: None,
    )
    source = InternalSignalSource(
        observation_only=False,
        ingestion_service=ingestion,
        publication_service=publication,
    )
    source.scan_file = lambda path: [result.signal]

    emitted = source.process_file("unused.csv")

    assert emitted == [result]
    assert publication.calls == ["INTERNAL:EMASVOL10:9004"]


def test_symbols_table_does_not_show_profile_column():
    from pathlib import Path

    source = (
        Path(__file__).parents[1]
        / "dashboard"
        / "pages"
        / "symbols_page.py"
    ).read_text(encoding="utf-8")
    table_definition = source.split(
        "self.table.setHorizontalHeaderLabels(", 1
    )[1].split(")", 1)[0]
    assert "self.table.setColumnCount(9)" in source
    assert '"Perfil"' not in table_definition
