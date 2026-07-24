from types import SimpleNamespace

from engine.profile_source_router import ProfileSourceRouter
from models.signal import Signal


def signal(source):
    return Signal(
        source=source,
        symbol="EmasVol20",
        external_signal_id="1" if source == "INTERNAL" else None,
        telegram_account_id=7 if source == "TELEGRAM" else None,
        chat_id=-100 if source == "TELEGRAM" else None,
        message_id=1 if source == "TELEGRAM" else None,
    )


def test_router_filters_profiles_without_other_responsibilities():
    profiles = [
        SimpleNamespace(signal_source_mode="OFF"),
        SimpleNamespace(signal_source_mode="TELEGRAM"),
        SimpleNamespace(signal_source_mode="INTERNAL"),
        SimpleNamespace(signal_source_mode="BOTH"),
    ]
    router = ProfileSourceRouter()

    assert router.filter(profiles, signal("TELEGRAM")) == [
        profiles[1],
        profiles[3],
    ]
    assert router.filter(profiles, signal("INTERNAL")) == [
        profiles[2],
        profiles[3],
    ]


def test_router_maps_legacy_profile_explicitly():
    router = ProfileSourceRouter()

    assert router.mode_for(SimpleNamespace(operation_mode="manual")) == "OFF"
    assert (
        router.mode_for(SimpleNamespace(operation_mode="telegram"))
        == "TELEGRAM"
    )
