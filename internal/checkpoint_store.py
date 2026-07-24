"""Checkpoint JSON independiente para observación de señales INTERNAL."""

import json
from pathlib import Path
from threading import Lock


class InternalCheckpointStore:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = Lock()
        self._keys = set()
        self.load()

    @staticmethod
    def key(external_signal_id):
        return f"INTERNAL:{str(external_signal_id).strip()}"

    def load(self):
        with self._lock:
            if not self.path.exists():
                self._keys = set()
                return set()
            try:
                payload = json.loads(
                    self.path.read_text(encoding="utf-8")
                )
                self._keys = {
                    str(value)
                    for value in payload.get("processed", [])
                }
            except (OSError, ValueError, TypeError, AttributeError):
                self._keys = set()
            return set(self._keys)

    def contains(self, external_signal_id):
        with self._lock:
            return self.key(external_signal_id) in self._keys

    def mark(self, external_signal_id):
        key = self.key(external_signal_id)
        with self._lock:
            if key in self._keys:
                return False
            self._keys.add(key)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(
                self.path.suffix + ".tmp"
            )
            temporary.write_text(
                json.dumps(
                    {"processed": sorted(self._keys)},
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary.replace(self.path)
            return True
