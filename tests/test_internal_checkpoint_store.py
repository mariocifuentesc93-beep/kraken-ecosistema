import json

from internal.checkpoint_store import InternalCheckpointStore


def test_checkpoint_loads_marks_and_persists(tmp_path):
    path = tmp_path / "internal-checkpoint.json"
    checkpoint = InternalCheckpointStore(path)

    assert checkpoint.contains("12304") is False
    assert checkpoint.mark("12304") is True
    assert checkpoint.mark("12304") is False
    assert checkpoint.contains("12304") is True

    reloaded = InternalCheckpointStore(path)
    assert reloaded.contains("12304") is True
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "processed": ["INTERNAL:12304"]
    }


def test_checkpoint_does_not_use_production_database(tmp_path):
    path = tmp_path / "observation" / "checkpoint.json"
    checkpoint = InternalCheckpointStore(path)

    checkpoint.mark("99")

    assert path.exists()
    assert path.suffix == ".json"
