from services.trading_calendar_service import TradingCalendarService


def test_reporting_filters_cover_current_operational_dimensions():
    row = {
        "profile_id": 1,
        "account_id": 2,
        "symbol": "LIONX40",
        "mode": "DEMO",
        "source": "INTERNAL",
        "status": "CLOSED",
        "direction": "SELL",
        "result": "WIN",
    }

    assert TradingCalendarService._matches(
        row,
        {
            "profile": "1",
            "account": "2",
            "symbol": "LIONX40",
            "mode": "DEMO",
            "source": "INTERNAL",
            "status": "CLOSED",
            "direction": "SELL",
            "result": "WIN",
        },
    )
    assert not TradingCalendarService._matches(row, {"mode": "SIMULATION"})
    assert not TradingCalendarService._matches(row, {"direction": "BUY"})
