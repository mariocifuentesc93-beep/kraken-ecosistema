"""Checkpoint JSON independiente para observación de señales INTERNAL."""

import json
from pathlib import Path
from threading import Lock

from models.signal import build_internal_idempotency_key


class InternalCheckpointStore:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = Lock()
        self._keys = set()
        self._level_snapshots = {}
        self.load()

    @staticmethod
    def key(symbol, external_signal_id):
        return build_internal_idempotency_key(
            symbol,
            external_signal_id,
        )

    def load(self):
        with self._lock:
            if not self.path.exists():
                self._keys = set()
                self._level_snapshots = {}
                return set()
            try:
                payload = json.loads(
                    self.path.read_text(encoding="utf-8")
                )
                self._keys = {
                    str(value)
                    for value in payload.get("processed", [])
                }
                self._level_snapshots = dict(
                    payload.get("level_snapshots", {})
                )
            except (OSError, ValueError, TypeError, AttributeError):
                self._keys = set()
                self._level_snapshots = {}
            return set(self._keys)

    def contains(self, symbol, external_signal_id):
        with self._lock:
            return self.key(symbol, external_signal_id) in self._keys

    def mark(self, symbol, external_signal_id):
        key = self.key(symbol, external_signal_id)
        with self._lock:
            if key in self._keys:
                return False
            self._keys.add(key)
            self._save()
            return True

    @staticmethod
    def _normalized_levels(stop_loss, take_profits):
        return {
            "stop_loss": float(stop_loss),
            "take_profits": [
                float(value) for value in list(take_profits or [])[:3]
            ],
        }

    def level_snapshot(self, symbol, external_signal_id):
        with self._lock:
            value = self._level_snapshots.get(
                self.key(symbol, external_signal_id)
            )
            return dict(value) if value is not None else None

    def update_level_snapshot(
        self, symbol, external_signal_id, stop_loss, take_profits
    ):
        key = self.key(symbol, external_signal_id)
        value = self._normalized_levels(stop_loss, take_profits)
        with self._lock:
            if self._level_snapshots.get(key) == value:
                return False
            self._level_snapshots[key] = value
            self._save()
            return True

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "processed": sorted(self._keys),
                    "level_snapshots": self._level_snapshots,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)
