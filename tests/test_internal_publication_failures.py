from internal.checkpoint_store import InternalCheckpointStore
from internal.source import InternalSignalSource
from tests.test_internal_ingestion_flow import (
    FIXTURES,
    PATTERN,
    RecordingSignalEngine,
)
from services.signal_ingestion_service import SignalIngestionService
from tests.test_internal_publication_service import profile, service
from tests.test_telegram_signal_publisher import FakeClient
from tests.test_telegram_signal_formatter import make_signal


def test_failed_send_is_recorded_and_explicit_retry_can_send(
    publication_repository,
):
    failing = FakeClient(RuntimeError("offline"))
    first_service = service(
        publication_repository,
        [profile()],
        failing,
    )
    first = first_service.publish(make_signal())
    row = publication_repository.get(
        "INTERNAL:LIONX100:12305",
        7,
        -100123,
    )
    assert first[0].status == "FAILED"
    assert row.attempt_count == 1
    assert row.last_error == "offline"

    successful = FakeClient()
    retry = service(
        publication_repository,
        [profile()],
        successful,
    ).publish(make_signal(), retry_failed=True)
    row = publication_repository.get_by_id(row.id)
    assert retry[0].sent is True
    assert row.status == "SENT"
    assert row.attempt_count == 2


class ExplodingPublicationService:
    def publish(self, signal, profiles):
        raise RuntimeError("telegram unavailable")


def test_publication_failure_does_not_change_ingestion_or_checkpoint(
    tmp_path,
    temporary_signal_repository,
):
    checkpoint = InternalCheckpointStore(tmp_path / "checkpoint.json")
    source = InternalSignalSource(
        directory=FIXTURES,
        pattern=PATTERN,
        checkpoint_store=checkpoint,
        observation_only=False,
        ingestion_service=SignalIngestionService(
            repository=temporary_signal_repository,
            signal_engine_instance=RecordingSignalEngine(result=True),
        ),
        publication_service=ExplodingPublicationService(),
    )
    result = source.scan_once()[0]
    assert result.accepted is True
    assert result.routed is True
    assert checkpoint.contains("EMASVOL20", "12304") is True
    assert source.scan_once() == []
