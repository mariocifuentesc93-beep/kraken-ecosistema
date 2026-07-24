from internal.csv_watcher import InternalCsvWatcher


def test_watcher_waits_for_stability_and_emits_each_version_once(
    tmp_path,
):
    path = tmp_path / "Kraken_BMSP_Test_M5.csv"
    path.write_text("header\n", encoding="utf-8")
    watcher = InternalCsvWatcher(
        tmp_path,
        stability_seconds=1.0,
    )

    assert watcher.scan_once(now=0.0) == []
    assert watcher.scan_once(now=0.5) == []
    assert watcher.scan_once(now=1.0) == [path]
    assert watcher.scan_once(now=2.0) == []

    path.write_text("header\nnew row\n", encoding="utf-8")
    assert watcher.scan_once(now=2.1) == []
    assert watcher.scan_once(now=3.0) == []
    assert watcher.scan_once(now=3.1) == [path]


def test_watcher_does_not_start_on_import_and_runs_in_background(
    tmp_path,
):
    emitted = []
    watcher = InternalCsvWatcher(
        tmp_path,
        callback=emitted.append,
        interval=0.01,
        stability_seconds=0.0,
    )

    assert watcher.running is False
    assert watcher.start() is True
    assert watcher.running is True
    watcher.stop()
    assert watcher.running is False
