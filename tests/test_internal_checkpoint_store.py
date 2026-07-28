import json

from internal.checkpoint_store import InternalCheckpointStore


def test_checkpoint_loads_marks_and_persists(tmp_path):
    path = tmp_path / "internal-checkpoint.json"
    checkpoint = InternalCheckpointStore(path)

    assert checkpoint.contains("EmasVol20", "12304") is False
    assert checkpoint.mark("EmasVol20", "12304") is True
    assert checkpoint.mark(" emasvol20 ", "12304") is False
    assert checkpoint.contains("EMASVOL20", "12304") is True

    reloaded = InternalCheckpointStore(path)
    assert reloaded.contains("EmasVol20", "12304") is True
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "processed": ["INTERNAL:EMASVOL20:12304"],
        "level_snapshots": {},
    }


def test_checkpoint_does_not_use_production_database(tmp_path):
    path = tmp_path / "observation" / "checkpoint.json"
    checkpoint = InternalCheckpointStore(path)

    checkpoint.mark("LionX75", "99")

    assert path.exists()
    assert path.suffix == ".json"


def test_checkpoint_distinguishes_same_id_between_symbols(tmp_path):
    checkpoint = InternalCheckpointStore(tmp_path / "checkpoint.json")

    assert checkpoint.mark("EmasVol20", "12304") is True
    assert checkpoint.mark("LionX75", "12304") is True
    assert checkpoint.mark(" emasvol20 ", "12304") is False
    assert checkpoint.contains("EMASVOL20", "12304") is True
    assert checkpoint.contains("LIONX75", "12304") is True


def test_level_snapshot_survives_restart_and_deduplicates(tmp_path):
    path = tmp_path / "checkpoint.json"
    checkpoint = InternalCheckpointStore(path)

    assert checkpoint.update_level_snapshot(
        "EmasVol20", "12304", 90, [110, 120, 130]
    )
    assert not checkpoint.update_level_snapshot(
        "EMASVOL20", "12304", 90, [110, 120, 130]
    )

    reloaded = InternalCheckpointStore(path)
    assert reloaded.level_snapshot(" emasvol20 ", "12304") == {
        "stop_loss": 90.0,
        "take_profits": [110.0, 120.0, 130.0],
    }
