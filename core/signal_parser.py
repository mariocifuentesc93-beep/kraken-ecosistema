import re

from config.symbols import get_symbols
from models.signal import Signal


# ==========================================================
# PARSER
# ==========================================================

def parse_signal(text):

    if not text:

        return None

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

    for symbol in get_symbols():

        if re.search(

            rf"\b{re.escape(symbol.upper())}\b",

            normalized,

        ):

            signal.symbol = symbol

            break

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

    if not signal.symbol:

        return None

    if not signal.direction:

        return None

    return signal