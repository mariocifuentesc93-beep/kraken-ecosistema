import re

from config.symbols import get_symbol_catalog, normalize_symbol
from models.signal import Signal


# ==========================================================
# PARSER
# ==========================================================

def parse_signal(text):

    if not text:

        return Signal(raw_message="")

    original_text = text

    normalized = text.upper()

    normalized = normalized.replace("\r", "")

    normalized = re.sub(r"[ \t]+", " ", normalized)

    normalized = normalized.strip()

    signal = Signal()

    signal.raw_message = original_text

    # =====================================================
    # SÍMBOLO
    # =====================================================

    for definition in get_symbol_catalog():
        canonical = definition["canonical_name"]
        display_pattern = r"\s+".join(
            re.escape(part)
            for part in definition["display_name"].upper().split()
        )
        if (
            re.search(rf"\b{re.escape(canonical)}\b", normalized)
            or re.search(rf"\b{display_pattern}\b", normalized)
        ):
            signal.symbol = canonical
            break

    if not signal.symbol:
        candidate = re.search(
            r"\b([A-Z][A-Z0-9 ]{2,}?)\s+(?:BUY|SELL)\b", normalized
        )
        if candidate:
            signal.symbol = (
                normalize_symbol(candidate.group(1)) or candidate.group(1).strip()
            )

    # =====================================================
    # DIRECCIÓN
    # =====================================================

    if re.search(r"\bBUY\b", normalized):

        signal.direction = "BUY"

    elif re.search(r"\bSELL\b", normalized):

        signal.direction = "SELL"

    # =====================================================
    # TIPO DE ENTRADA
    # =====================================================

    entry_type = "MARKET"

    if re.search(r"\bLIMIT\b", normalized):

        entry_type = "LIMIT"

    elif re.search(r"\bSTOP\b", normalized):

        entry_type = "STOP"

    signal.metadata["entry_type"] = entry_type

    # =====================================================
    # ENTRY
    # =====================================================

    entry_patterns = [

        r"\bENTRY\s*[:=@-]?\s*(\d+(?:\.\d+)?)",

        r"\bPRICE\s*[:=@-]?\s*(\d+(?:\.\d+)?)",

        r"\bOPEN\s*[:=@-]?\s*(\d+(?:\.\d+)?)",

    ]

    for pattern in entry_patterns:

        match = re.search(pattern, normalized)

        if match:

            signal.entry = float(match.group(1))

            break

    # =====================================================
    # STOP LOSS
    # =====================================================

    sl_patterns = [

        r"\bSL\s*[:=@-]?\s*(\d+(?:\.\d+)?)",

        r"\bSTOP LOSS\s*[:=@-]?\s*(\d+(?:\.\d+)?)",

    ]

    for pattern in sl_patterns:

        match = re.search(pattern, normalized)

        if match:

            signal.stop_loss = float(match.group(1))

            break

    # =====================================================
    # TAKE PROFITS
    # =====================================================

    tp_matches = re.findall(

        r"\bTP\d*\s*[:=@-]?\s*(\d+(?:\.\d+)?)",

        normalized,

    )

    signal.take_profits = [

        float(tp)

        for tp in tp_matches

    ]

    # =====================================================
    # MERCADO
    # =====================================================

    if signal.entry == 0:

        signal.metadata["market_execution"] = True

    else:

        signal.metadata["market_execution"] = False

    # =====================================================
    # VALIDACIÓN
    # =====================================================

    return signal
