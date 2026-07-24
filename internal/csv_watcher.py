"""Watcher no bloqueante para detectar CSV estables del inspector."""

import threading
import time
from pathlib import Path


class InternalCsvWatcher:
    def __init__(
        self,
        directory,
        callback=None,
        interval=1.0,
        stability_seconds=1.0,
        pattern="Kraken_BMSP_*.csv",
        clock=None,
    ):
        self.directory = Path(directory)
        self.callback = callback
        self.interval = float(interval)
        self.stability_seconds = float(stability_seconds)
        self.pattern = pattern
        self._clock = clock or time.monotonic
        self._observed = {}
        self._emitted = {}
        self._stop_event = threading.Event()
        self._thread = None
        self.state = "STOPPED"
        self.last_error = ""

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def scan_once(self, now=None):
        now = self._clock() if now is None else float(now)
        stable = []
        if not self.directory.exists():
            return stable

        for path in sorted(self.directory.glob(self.pattern)):
            try:
                stat = path.stat()
            except OSError:
                continue
            signature = (stat.st_size, stat.st_mtime_ns)
            previous = self._observed.get(path)
            if previous is None or previous["signature"] != signature:
                self._observed[path] = {
                    "signature": signature,
                    "stable_since": now,
                }
                continue
            if now - previous["stable_since"] < self.stability_seconds:
                continue
            if self._emitted.get(path) == signature:
                continue
            self._emitted[path] = signature
            stable.append(path)
        return stable

    def _run(self):
        try:
            while not self._stop_event.is_set():
                for path in self.scan_once():
                    if self.callback is not None:
                        self.callback(path)
                self._stop_event.wait(self.interval)
        except Exception as error:
            self.last_error = str(error)
            self.state = "ERROR"
        finally:
            if self.state != "ERROR":
                self.state = "STOPPED"

    def start(self):
        if self.running:
            return False
        self.state = "STARTING"
        self.last_error = ""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="KrakenInternalCsvWatcher",
            daemon=True,
        )
        self._thread.start()
        self.state = "RUNNING"
        return True

    def stop(self, timeout=5.0):
        if self._thread is None:
            self.state = "STOPPED"
            return False
        self.state = "STOPPING"
        self._stop_event.set()
        self._thread.join(timeout)
        self._thread = None
        if self.state != "ERROR":
            self.state = "STOPPED"
        return True
