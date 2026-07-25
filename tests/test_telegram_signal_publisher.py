from telegram.signal_publisher import TelegramSignalPublisher
from tests.test_telegram_signal_formatter import make_signal


class FakeClient:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def send_message(self, chat_id, message):
        if self.error:
            raise self.error
        self.calls.append((chat_id, message))
        return {"id": 1}


def test_publisher_uses_injected_client_and_plain_text():
    client = FakeClient()
    publisher = TelegramSignalPublisher(lambda account_id: client)
    result = publisher.publish(make_signal(), 7, -100123)
    assert result.success is True
    assert result.message_id == 1
    assert len(client.calls) == 1
    assert client.calls[0][0] == -100123
    assert "Signal ID: 12305" in client.calls[0][1]


def test_publisher_returns_controlled_failure():
    publisher = TelegramSignalPublisher(
        lambda account_id: FakeClient(RuntimeError("offline"))
    )
    result = publisher.publish(make_signal(), 7, -100123)
    assert result.success is False
    assert result.error == "offline"
    assert "RuntimeError: offline" in result.traceback
