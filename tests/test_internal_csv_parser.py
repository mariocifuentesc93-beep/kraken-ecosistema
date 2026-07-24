from pathlib import Path

from internal.csv_parser import parse_csv, parse_decimal


FIXTURES = Path(__file__).parent / "fixtures" / "internal_csv"


def test_parser_supports_utf8_sig_unknown_columns_and_decimal_points():
    rows = parse_csv(FIXTURES / "Kraken_BMSP_buy_complete.csv")

    assert len(rows) == 7
    assert rows[0].object_name == "BMSP_12304_entry_label"
    assert rows[1].price_0 == 73505.99
    assert rows[0].raw["unknown_column"] == "ignored"


def test_parser_accepts_comma_decimal():
    rows = parse_csv(FIXTURES / "Kraken_BMSP_comma_decimal.csv")

    assert rows[0].price_0 == 73505.99
    assert parse_decimal("1.234,56") == 1234.56
    assert parse_decimal("1,234.56") == 1234.56


def test_parser_tolerates_partially_written_and_incomplete_rows():
    rows = parse_csv(FIXTURES / "Kraken_BMSP_partial.csv")

    assert len(rows) == 3
    assert rows[-1].object_name == "BMSP_40001_tp1_line"
    assert rows[-1].price_0 is None
