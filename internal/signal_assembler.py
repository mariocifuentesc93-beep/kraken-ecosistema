"""Reconstrucción de señales a partir de objetos BMSP normalizados."""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from internal.csv_parser import ParsedObjectRow


OBJECT_PATTERN = re.compile(
    r"^BMSP_(?P<signal_id>\d+)_"
    r"(?P<part>entry|sl|tp1|tp2|tp3)_(?P<kind>line|label)$",
    re.IGNORECASE,
)
TRIANGLE_PATTERN = re.compile(
    r"^BMSP_(?P<signal_id>\d+)_triangle$",
    re.IGNORECASE,
)
SIGNAL_ID_PATTERN = re.compile(r"#?\b(\d+)\b")
DIRECTION_PATTERN = re.compile(r"\b(BUY|SELL)\b", re.IGNORECASE)


@dataclass(frozen=True)
class AssembledInternalSignal:
    external_signal_id: str
    symbol: str
    direction: str
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    detected_at: Optional[datetime]
    source_file: Path


def _direction_from_text(*values) -> Optional[str]:
    for value in values:
        normalized = str(value or "").replace("_", " ").replace("-", " ")
        match = DIRECTION_PATTERN.search(normalized)
        if match:
            return match.group(1).upper()
    return None


def _banner_hint(row):
    if row.object_name.upper() != "BMSP_BANNER_NEW":
        return None
    text = f"{row.text} {row.tooltip}"
    direction = _direction_from_text(text)
    id_match = SIGNAL_ID_PATTERN.search(text)
    return {
        "symbol": row.symbol,
        "signal_id": id_match.group(1) if id_match else None,
        "direction": direction,
        "scan_time": row.scan_time,
    }


def _new_group(row, signal_id):
    return {
        "signal_id": signal_id,
        "symbol": row.symbol,
        "source_file": row.source_file,
        "detected_at": row.scan_time,
        "direction": None,
        "values": {},
        "kinds": {},
        "sequence": {},
    }


def _select_price(group, part, kind, price, sequence):
    if price is None:
        return
    previous_kind = group["kinds"].get(part)
    previous_sequence = group["sequence"].get(part, -1)
    should_replace = (
        previous_kind is None
        or (kind == "line" and previous_kind != "line")
        or (kind == previous_kind and sequence >= previous_sequence)
    )
    if should_replace:
        group["values"][part] = price
        group["kinds"][part] = kind
        group["sequence"][part] = sequence


def assemble_signals(
    rows: Iterable[ParsedObjectRow],
) -> List[AssembledInternalSignal]:
    groups: Dict[Tuple[str, str], dict] = {}
    banners = []

    for sequence, row in enumerate(rows):
        banner = _banner_hint(row)
        if banner:
            banners.append(banner)
            continue

        object_match = OBJECT_PATTERN.match(row.object_name)
        triangle_match = TRIANGLE_PATTERN.match(row.object_name)
        if not object_match and not triangle_match:
            continue

        signal_id = (
            object_match.group("signal_id")
            if object_match
            else triangle_match.group("signal_id")
        )
        if not row.symbol or not signal_id.isdigit():
            continue
        key = (row.symbol, signal_id)
        group = groups.setdefault(key, _new_group(row, signal_id))

        if row.scan_time is not None:
            current = group["detected_at"]
            if current is None or row.scan_time < current:
                group["detected_at"] = row.scan_time

        direction = _direction_from_text(row.text, row.tooltip)
        if direction:
            group["direction"] = direction
        if triangle_match:
            arrow_direction = _direction_from_text(row.object_type)
            if arrow_direction:
                group["direction"] = arrow_direction
            continue

        part = object_match.group("part").lower()
        kind = object_match.group("kind").lower()
        _select_price(group, part, kind, row.price_0, sequence)

    for group in groups.values():
        if group["direction"]:
            continue
        exact_hints = [
            hint
            for hint in banners
            if hint["symbol"] == group["symbol"]
            and hint["signal_id"] == group["signal_id"]
            and hint["direction"]
        ]
        fallback_hints = [
            hint
            for hint in banners
            if hint["symbol"] == group["symbol"]
            and hint["signal_id"] is None
            and hint["direction"]
        ]
        hint = (
            exact_hints[-1]
            if exact_hints
            else fallback_hints[-1]
            if len(fallback_hints) == 1
            else None
        )
        if hint:
            group["direction"] = hint["direction"]
            if group["detected_at"] is None:
                group["detected_at"] = hint["scan_time"]

    assembled = []
    required = ("entry", "sl", "tp1", "tp2", "tp3")
    for group in groups.values():
        if not group["direction"]:
            continue
        if any(part not in group["values"] for part in required):
            continue
        values = group["values"]
        assembled.append(
            AssembledInternalSignal(
                external_signal_id=group["signal_id"],
                symbol=group["symbol"],
                direction=group["direction"],
                entry=values["entry"],
                stop_loss=values["sl"],
                tp1=values["tp1"],
                tp2=values["tp2"],
                tp3=values["tp3"],
                detected_at=group["detected_at"],
                source_file=group["source_file"],
            )
        )

    return sorted(
        assembled,
        key=lambda item: (
            item.symbol,
            int(item.external_signal_id),
        ),
    )
