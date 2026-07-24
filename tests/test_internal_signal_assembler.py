from pathlib import Path

from internal.csv_parser import parse_csv
from internal.signal_assembler import assemble_signals


FIXTURES = Path(__file__).parent / "fixtures" / "internal_csv"


def assembled(filename):
    return assemble_signals(parse_csv(FIXTURES / filename))


def test_reconstructs_complete_buy_and_prefers_line_price():
    result = assembled("Kraken_BMSP_buy_complete.csv")

    assert len(result) == 1
    signal = result[0]
    assert signal.external_signal_id == "12304"
    assert signal.symbol == "EmasVol20"
    assert signal.direction == "BUY"
    assert signal.entry == 73505.99
    assert signal.stop_loss == 73486.47
    assert (signal.tp1, signal.tp2, signal.tp3) == (
        73517.7,
        73529.41,
        73545.02,
    )


def test_reconstructs_sell_from_arrow():
    signal = assembled("Kraken_BMSP_sell_complete.csv")[0]

    assert signal.direction == "SELL"
    assert signal.external_signal_id == "12305"


def test_two_signals_and_same_id_in_different_symbols_are_distinct():
    assert len(assembled("Kraken_BMSP_two_signals.csv")) == 2
    same_id = assembled("Kraken_BMSP_same_id_symbols.csv")

    assert len(same_id) == 2
    assert {item.symbol for item in same_id} == {
        "EmasVol80",
        "LionX100",
    }
    assert {item.external_signal_id for item in same_id} == {"70001"}


def test_hud_and_incomplete_signals_are_not_emitted():
    assert assembled("Kraken_BMSP_hud_ignored.csv") == []
    assert assembled("Kraken_BMSP_incomplete.csv") == []
    assert assembled("Kraken_BMSP_partial.csv") == []


def test_repeated_updates_do_not_duplicate_and_latest_line_wins():
    result = assembled("Kraken_BMSP_repeated_updates.csv")

    assert len(result) == 1
    assert result[0].entry == 100.5


def test_banner_supplies_direction_when_objects_do_not():
    signal = assembled("Kraken_BMSP_banner_new.csv")[0]

    assert signal.external_signal_id == "80001"
    assert signal.direction == "SELL"
