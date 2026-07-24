from types import SimpleNamespace

from engine.runtime import RuntimeStatus
from services.runtime_coordinator import RuntimeCoordinator
from engine.kraken_engine import KrakenEngine


class Component:
    def __init__(self):
        self.starts = 0
        self.stops = 0
        self.state = RuntimeStatus.STOPPED

    def start(self):
        self.starts += 1
        self.state = RuntimeStatus.RUNNING
        return True

    def stop(self):
        self.stops += 1
        self.state = RuntimeStatus.STOPPED
        return True


class Source:
    directory = "."

    def __init__(self):
        self.paths = []

    def process_file(self, path):
        self.paths.append(path)


def coordinator():
    telegram = Component()
    watcher = Component()
    watcher.last_error = ""
    source = Source()
    signal = Component()
    execution = Component()
    monitor = Component()
    runtime = RuntimeCoordinator(
        telegram_runtime=telegram,
        internal_watcher=watcher,
        internal_source=source,
        signal_engine=signal,
        execution_engine=execution,
        operation_monitor=monitor,
    )
    return runtime, telegram, watcher, signal, execution, monitor


def test_runtime_start_and_stop_are_idempotent():
    runtime, telegram, watcher, signal, execution, monitor = coordinator()
    assert runtime.start() is True
    assert runtime.start() is False
    assert runtime.get_status().state == RuntimeStatus.RUNNING
    assert all(
        item.starts == 1
        for item in (telegram, watcher, signal, execution, monitor)
    )
    assert runtime.stop() is True
    assert runtime.stop() is False
    assert all(
        item.stops == 1
        for item in (telegram, watcher, signal, execution, monitor)
    )


def test_internal_callback_error_is_visible_without_duplicate_runtime():
    runtime, *_ = coordinator()
    runtime._internal_source = SimpleNamespace(
        process_file=lambda path: (_ for _ in ()).throw(
            RuntimeError("CSV inválido")
        )
    )
    try:
        runtime._process_internal_file("signal.csv")
    except RuntimeError:
        pass
    assert runtime.internal_state == RuntimeStatus.ERROR
    assert runtime.last_error == "CSV inválido"


def test_kraken_engine_delegates_to_one_runtime():
    runtime = Component()
    runtime.get_status = lambda: "snapshot"
    engine = KrakenEngine(runtime_coordinator_instance=runtime)
    engine.start()
    engine.start()
    assert runtime.starts == 1
    assert engine.get_status() == "snapshot"
    engine.stop()
    engine.stop()
    assert runtime.stops == 1


def test_professional_window_and_app_share_global_engine():
    from dashboard import main_window
    from engine.kraken_engine import kraken_engine

    assert main_window.kraken_engine is kraken_engine
