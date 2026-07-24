"""Conversión y ejecución manual de INTERNAL en modo observación."""

import argparse
import logging
import os
from datetime import datetime
from pathlib import Path

from internal.checkpoint_store import InternalCheckpointStore
from internal.csv_parser import parse_csv
from internal.signal_assembler import assemble_signals
from models.signal import Signal


def default_internal_directory():
    appdata = os.environ.get("APPDATA")
    if appdata:
        return (
            Path(appdata)
            / "MetaQuotes"
            / "Terminal"
            / "Common"
            / "Files"
        )
    return Path.cwd()


def format_internal_signal(signal):
    targets = list(signal.take_profits) + [0.0, 0.0, 0.0]
    return (
        f"SIGNAL - {signal.symbol} ({signal.direction})\n\n"
        f"Entry: {signal.entry}\n"
        f"SL: {signal.stop_loss}\n"
        f"TP1: {targets[0]}\n"
        f"TP2: {targets[1]}\n"
        f"TP3: {targets[2]}\n\n"
        f"ID interno Kraken: {signal.external_signal_id}"
    )


def to_signal(assembled, received_at=None):
    received_at = received_at or datetime.now()
    raw_message = (
        f"SIGNAL - {assembled.symbol} ({assembled.direction})\n"
        f"Entry: {assembled.entry}\n"
        f"SL: {assembled.stop_loss}\n"
        f"TP1: {assembled.tp1}\n"
        f"TP2: {assembled.tp2}\n"
        f"TP3: {assembled.tp3}\n"
        f"ID interno Kraken: {assembled.external_signal_id}"
    )
    signal = Signal(
        source="INTERNAL",
        external_signal_id=assembled.external_signal_id,
        symbol=assembled.symbol,
        direction=assembled.direction,
        entry=assembled.entry,
        stop_loss=assembled.stop_loss,
        take_profits=[
            assembled.tp1,
            assembled.tp2,
            assembled.tp3,
        ],
        detected_at=assembled.detected_at,
        received_at=received_at,
        raw_message=raw_message,
        metadata={
            "source_file": str(assembled.source_file),
            "inspector": "KrakenBMSPInspector",
            "original_signal_id": assembled.external_signal_id,
        },
    )
    signal.validate_persistent_identity()
    return signal


class InternalSignalSource:
    def __init__(
        self,
        directory=None,
        checkpoint_store=None,
        pattern="Kraken_BMSP_*.csv",
        observation_only=True,
        ingestion_service=None,
        logger=None,
    ):
        self.directory = Path(directory or default_internal_directory())
        self.pattern = pattern
        self.checkpoint_store = checkpoint_store
        self.observation_only = bool(observation_only)
        self._ingestion_service = ingestion_service
        self._logger = logger or logging.getLogger(__name__)

    def _get_ingestion_service(self):
        if self._ingestion_service is None:
            raise RuntimeError(
                "ingestion_service es obligatorio cuando "
                "observation_only=False"
            )
        return self._ingestion_service

    def scan_file(self, path):
        return [
            to_signal(item)
            for item in assemble_signals(parse_csv(path))
        ]

    def process_file(self, path):
        detected = []
        for signal in self.scan_file(path):
            if (
                self.checkpoint_store is not None
                and self.checkpoint_store.contains(
                    signal.symbol,
                    signal.external_signal_id
                )
            ):
                continue
            if self.observation_only:
                detected.append(signal)
                if self.checkpoint_store is not None:
                    self.checkpoint_store.mark(
                        signal.symbol,
                        signal.external_signal_id
                    )
                continue

            try:
                result = self._get_ingestion_service().ingest(signal)
            except Exception as error:
                self._logger.exception(
                    "Fallo transitorio ingiriendo INTERNAL %s: %s",
                    signal.idempotency_key,
                    error,
                )
                continue

            detected.append(result)
            conclusive = bool(
                getattr(result, "created", False)
                or getattr(result, "duplicate", False)
            )
            if conclusive and self.checkpoint_store is not None:
                self.checkpoint_store.mark(
                    signal.symbol,
                    signal.external_signal_id
                )
        return detected

    def scan_once(self):
        detected = []
        for path in sorted(self.directory.glob(self.pattern)):
            detected.extend(self.process_file(path))
        return detected


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Observa señales KrakenBMSPInspector sin ejecutarlas."
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=default_internal_directory(),
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
    )
    arguments = parser.parse_args(argv)
    checkpoint = (
        InternalCheckpointStore(arguments.checkpoint)
        if arguments.checkpoint
        else None
    )
    source = InternalSignalSource(
        directory=arguments.directory,
        checkpoint_store=checkpoint,
    )
    for signal in source.scan_once():
        print(format_internal_signal(signal))
        print()


if __name__ == "__main__":
    main()
