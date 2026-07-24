"""Parser tolerante para los CSV generados por KrakenBMSPInspector."""

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


def parse_decimal(value) -> Optional[float]:
    if value is None:
        return None
    normalized = str(value).strip().replace(" ", "")
    if not normalized:
        return None
    if "," in normalized and "." not in normalized:
        normalized = normalized.replace(",", ".")
    elif "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    try:
        return float(normalized)
    except (TypeError, ValueError):
        return None


def parse_datetime(value) -> Optional[datetime]:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    normalized = normalized.replace("Z", "+00:00")
    for candidate in (
        normalized,
        normalized.replace(".", "-"),
    ):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass
    for format_string in (
        "%Y.%m.%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(normalized, format_string)
        except ValueError:
            pass
    return None


@dataclass(frozen=True)
class ParsedObjectRow:
    source_file: Path
    symbol: str
    object_name: str
    object_type: str
    text: str = ""
    tooltip: str = ""
    event: str = ""
    timeframe: str = ""
    price_0: Optional[float] = None
    price_1: Optional[float] = None
    price_2: Optional[float] = None
    scan_time: Optional[datetime] = None
    raw: Dict[str, str] = field(default_factory=dict)


def _normalize_header(value) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _normalized_mapping(row) -> Dict[str, str]:
    normalized = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized[_normalize_header(key)] = (
            "" if value is None else str(value).strip()
        )
    return normalized


def normalize_row(row, source_file) -> Optional[ParsedObjectRow]:
    values = _normalized_mapping(row)
    object_name = values.get("object_name") or values.get("name") or ""
    symbol = values.get("symbol") or ""
    if not object_name:
        return None

    return ParsedObjectRow(
        source_file=Path(source_file),
        symbol=symbol.strip(),
        object_name=object_name.strip(),
        object_type=(
            values.get("object_type") or values.get("type") or ""
        ).strip(),
        text=values.get("text", ""),
        tooltip=values.get("tooltip", ""),
        event=values.get("event", ""),
        timeframe=values.get("timeframe", ""),
        price_0=parse_decimal(
            values.get("price_0", values.get("price"))
        ),
        price_1=parse_decimal(values.get("price_1")),
        price_2=parse_decimal(values.get("price_2")),
        scan_time=parse_datetime(
            values.get("scan_time", values.get("detected_at"))
        ),
        raw=values,
    )


def parse_lines(
    lines: Iterable[str],
    source_file="<memory>",
) -> List[ParsedObjectRow]:
    reader = csv.DictReader(lines, delimiter=";")
    if not reader.fieldnames:
        return []
    rows = []
    for raw_row in reader:
        try:
            row = normalize_row(raw_row, source_file)
        except (csv.Error, TypeError, ValueError):
            continue
        if row is not None:
            rows.append(row)
    return rows


def parse_csv(path) -> List[ParsedObjectRow]:
    path = Path(path)
    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            errors="replace",
            newline="",
        ) as stream:
            return parse_lines(stream, source_file=path)
    except (OSError, csv.Error):
        return []
