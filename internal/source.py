"""Conversión y ejecución manual de INTERNAL en modo observación."""

import argparse
import logging
import os
import traceback
from datetime import datetime
from pathlib import Path

from internal.checkpoint_store import InternalCheckpointStore
from internal.csv_parser import parse_csv
from internal.signal_assembler import assemble_signals
from internal.signal_level_update import InternalSignalLevelUpdate
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
        publication_service=None,
        level_update_service=None,
        logger=None,
    ):
        self.directory = Path(directory or default_internal_directory())
        self.pattern = pattern
        self.checkpoint_store = checkpoint_store
        self.observation_only = bool(observation_only)
        self._ingestion_service = ingestion_service
        self._publication_service = publication_service
        self._level_update_service = level_update_service
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
            previous_levels = (
                self.checkpoint_store.level_snapshot(
                    signal.symbol, signal.external_signal_id
                )
                if self.checkpoint_store is not None
                and hasattr(self.checkpoint_store, "level_snapshot")
                else None
            )
            current_levels = {
                "stop_loss": float(signal.stop_loss),
                "take_profits": [
                    float(value) for value in signal.take_profits[:3]
                ],
            }
            # KrakenPro puede eliminar y recrear un objeto durante el mismo
            # redibujado. Un cero intermedio no representa una actualización
            # operativa y no debe modificar MT5, el checkpoint ni Telegram.
            levels_are_complete = (
                current_levels["stop_loss"] > 0
                and len(current_levels["take_profits"]) == 3
                and all(
                    value > 0
                    for value in current_levels["take_profits"]
                )
            )
            if (
                self.checkpoint_store is not None
                and self.checkpoint_store.contains(
                    signal.symbol,
                    signal.external_signal_id
                )
            ):
                if not levels_are_complete:
                    continue
                if previous_levels is None:
                    self.checkpoint_store.update_level_snapshot(
                        signal.symbol,
                        signal.external_signal_id,
                        signal.stop_loss,
                        signal.take_profits,
                    )
                elif (
                    previous_levels != current_levels
                    and self._level_update_service is not None
                ):
                    update = InternalSignalLevelUpdate(
                        symbol=signal.symbol,
                        external_signal_id=signal.external_signal_id,
                        direction=signal.direction,
                        previous_stop_loss=float(
                            previous_levels["stop_loss"]
                        ),
                        stop_loss=float(signal.stop_loss),
                        previous_take_profits=tuple(
                            previous_levels["take_profits"]
                        ),
                        take_profits=tuple(signal.take_profits[:3]),
                        detected_at=datetime.now(),
                    )
                    self._level_update_service.apply(update)
                    self.checkpoint_store.update_level_snapshot(
                        signal.symbol,
                        signal.external_signal_id,
                        signal.stop_loss,
                        signal.take_profits,
                    )
                continue
            if self.observation_only:
                detected.append(signal)
                if self.checkpoint_store is not None:
                    self.checkpoint_store.mark(
                        signal.symbol,
                        signal.external_signal_id
                    )
                    self.checkpoint_store.update_level_snapshot(
                        signal.symbol,
                        signal.external_signal_id,
                        signal.stop_loss,
                        signal.take_profits,
                    )
                continue

            try:
                ingestion = self._get_ingestion_service()
                if hasattr(ingestion, "record_event"):
                    ingestion.record_event(
                        signal,
                        "PARSED",
                        (
                            f"Archivo={path} | direction={signal.direction} | "
                            f"entry={signal.entry} | stop_loss={signal.stop_loss} | "
                            f"take_profits={signal.take_profits}"
                        ),
                    )
                result = ingestion.ingest(signal)
            except Exception as error:
                self._logger.exception(
                    "Fallo transitorio ingiriendo INTERNAL %s: %s",
                    signal.idempotency_key,
                    error,
                )
                continue

            detected.append(result)
            if (
                getattr(result, "created", False)
                and getattr(result, "signal", None) is not None
                and self._publication_service is not None
            ):
                try:
                    destination = (
                        self._publication_service.destination_details()
                        if hasattr(
                            self._publication_service,
                            "destination_details",
                        )
                        else {}
                    )
                    if hasattr(ingestion, "record_event"):
                        ingestion.record_event(
                            result.signal,
                            "TELEGRAM_PUBLICATION_START",
                            (
                                "Inicio de publicación global | "
                                f"telegram_account_id={destination.get('telegram_account_id')} | "
                                f"telegram_channel_id={destination.get('telegram_channel_id')} | "
                                f"chat_id={destination.get('chat_id')} | "
                                f"destination_error={destination.get('error') or '-'}"
                            ),
                        )
                    publication_results = self._publication_service.publish(
                        result.signal
                    )
                    publication_status = "SKIPPED"
                    for publication in publication_results:
                        if (
                            getattr(publication, "sent", False)
                            or getattr(
                                publication, "already_sent", False
                            )
                        ):
                            publication_status = "SUCCESS"
                        elif (
                            getattr(publication, "status", "")
                            == "FAILED"
                        ):
                            publication_status = "FAILED"
                        if hasattr(ingestion, "record_event"):
                            level = (
                                "error"
                                if publication_status == "FAILED"
                                else "info"
                            )
                            ingestion.record_event(
                                result.signal,
                                "TELEGRAM_PUBLICATION",
                                (
                                    f"status={publication_status} | "
                                    f"telegram_account_id={getattr(publication, 'telegram_account_id', None)} | "
                                    f"telegram_channel_id={getattr(publication, 'telegram_channel_id', None)} | "
                                    f"chat_id={getattr(publication, 'chat_id', None)} | "
                                    f"message_id={getattr(publication, 'message_id', None)} | "
                                    f"error={getattr(publication, 'error', None) or '-'} | "
                                    f"traceback={getattr(publication, 'traceback', None) or '-'}"
                                ),
                                level=level,
                            )
                    result.signal.metadata["publication_status"] = (
                        publication_status
                    )
                    result.signal.metadata["publication_results"] = [
                        {
                            "status": getattr(item, "status", ""),
                            "telegram_account_id": getattr(
                                item, "telegram_account_id", None
                            ),
                            "telegram_channel_id": getattr(
                                item, "telegram_channel_id", None
                            ),
                            "chat_id": getattr(item, "chat_id", None),
                            "message_id": getattr(item, "message_id", None),
                            "error": getattr(item, "error", None),
                            "traceback": getattr(item, "traceback", None),
                        }
                        for item in publication_results
                    ]
                    if hasattr(ingestion, "update_outcome"):
                        ingestion.update_outcome(result.signal)
                except Exception as error:
                    error_traceback = traceback.format_exc()
                    self._logger.exception(
                        "La publicación opcional falló para %s: %s",
                        signal.idempotency_key,
                        error,
                    )
                    result.signal.metadata["publication_status"] = "FAILED"
                    result.signal.metadata["publication_error"] = str(error)
                    result.signal.metadata["publication_traceback"] = (
                        error_traceback
                    )
                    if hasattr(ingestion, "update_outcome"):
                        ingestion.update_outcome(result.signal)
                    if hasattr(ingestion, "record_event"):
                        ingestion.record_event(
                            result.signal,
                            "TELEGRAM_PUBLICATION",
                            f"{error}\n{error_traceback}",
                            level="error",
                        )
            conclusive = bool(
                getattr(result, "created", False)
                or getattr(result, "duplicate", False)
            )
            if conclusive and self.checkpoint_store is not None:
                self.checkpoint_store.mark(
                    signal.symbol,
                    signal.external_signal_id
                )
                self.checkpoint_store.update_level_snapshot(
                    signal.symbol,
                    signal.external_signal_id,
                    signal.stop_loss,
                    signal.take_profits,
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
