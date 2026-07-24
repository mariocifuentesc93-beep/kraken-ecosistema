import asyncio
from types import SimpleNamespace

from telegram.listener import register_telegram_listener


class FakeClient:
    def __init__(self):
        self.handler = None

    def on(self, _event):
        def register(handler):
            self.handler = handler
            return handler
        return register


def test_listener_produces_unified_telegram_contract():
    client = FakeClient()
    captured = {}

    def processor(**kwargs):
        captured.update(kwargs)

    register_telegram_listener(
        client,
        account_id=7,
        signal_processor=processor,
    )
    event = SimpleNamespace(
        chat_id=-100123,
        message=SimpleNamespace(
            id=99,
            message=(
                "SIGNAL - EmasVol20 (buy)\n"
                "Entry: 73505.99\n"
                "SL: 73486.47\n"
                "TP1: 73517.70\n"
                "TP2: 73529.41\n"
                "TP3: 73545.02"
            ),
        ),
    )

    asyncio.run(client.handler(event))
    signal = captured["signal"]

    assert signal.source == "TELEGRAM"
    assert signal.telegram_account_id == 7
    assert signal.chat_id == -100123
    assert signal.message_id == 99
    assert signal.idempotency_key == "TELEGRAM:7:-100123:99"
    assert signal.symbol == "EMASVOL20"
    assert signal.take_profits == [73517.70, 73529.41, 73545.02]
