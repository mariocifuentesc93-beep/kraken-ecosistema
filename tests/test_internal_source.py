from datetime import datetime
from pathlib import Path
import subprocess
import sys

from internal.csv_parser import parse_csv
from internal.signal_assembler import assemble_signals
from internal.source import (
    InternalSignalSource,
    format_internal_signal,
    to_signal,
)


FIXTURES = Path(__file__).parent / "fixtures" / "internal_csv"


def test_assembled_signal_converts_to_unified_internal_signal():
    assembled = assemble_signals(
        parse_csv(FIXTURES / "Kraken_BMSP_buy_complete.csv")
    )[0]
    received_at = datetime(2026, 7, 23, 10, 5)

    signal = to_signal(assembled, received_at=received_at)

    assert signal.source == "INTERNAL"
    assert signal.external_signal_id == "12304"
    assert signal.idempotency_key == "INTERNAL:12304"
    assert signal.take_profits == [73517.7, 73529.41, 73545.02]
    assert signal.received_at == received_at
    assert signal.detected_at == datetime(2026, 7, 23, 10, 0)
    assert signal.metadata["inspector"] == "KrakenBMSPInspector"
    assert signal.metadata["original_signal_id"] == "12304"
    assert signal.metadata["source_file"].endswith(
        "Kraken_BMSP_buy_complete.csv"
    )


def test_observation_format_keeps_internal_id():
    source = InternalSignalSource(directory=FIXTURES)
    signal = source.scan_file(
        FIXTURES / "Kraken_BMSP_buy_complete.csv"
    )[0]
    output = format_internal_signal(signal)

    assert "SIGNAL - EmasVol20 (BUY)" in output
    assert "Entry: 73505.99" in output
    assert "TP3: 73545.02" in output
    assert "ID interno Kraken: 12304" in output


def test_importing_source_does_not_import_operational_pipeline():
    repository_root = Path(__file__).resolve().parents[1]
    script = (
        "import sys; import internal.source; "
        "blocked=['services.signal_ingestion_service',"
        "'engine.signal_engine','MetaTrader5','telethon']; "
        "print(','.join(x for x in blocked if x in sys.modules))"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == ""
