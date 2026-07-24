import pytest

from core.signal_sources import (
    SignalSourceMode,
    accepts_signal_source,
    normalize_signal_source_mode,
    source_mode_from_operation_mode,
)
from models.profile import Profile


@pytest.mark.parametrize(
    ("mode", "telegram", "internal"),
    [
        (SignalSourceMode.OFF, False, False),
        (SignalSourceMode.TELEGRAM, True, False),
        (SignalSourceMode.INTERNAL, False, True),
        (SignalSourceMode.BOTH, True, True),
    ],
)
def test_source_mode_semantics(mode, telegram, internal):
    assert accepts_signal_source(mode, "TELEGRAM") is telegram
    assert accepts_signal_source(mode, "INTERNAL") is internal


def test_source_mode_normalization_and_legacy_mapping():
    assert normalize_signal_source_mode(" both ") == "BOTH"
    assert source_mode_from_operation_mode("telegram") == "TELEGRAM"
    assert source_mode_from_operation_mode("both") == "BOTH"
    assert source_mode_from_operation_mode("manual") == "OFF"
    assert source_mode_from_operation_mode("unknown") == "OFF"


def test_unknown_source_mode_is_rejected():
    with pytest.raises(ValueError):
        normalize_signal_source_mode("invalid")


def test_profile_keeps_source_and_execution_modes_separate():
    profile = Profile(
        signal_source_mode=" internal ",
        execution_mode="SIMULATION",
    )

    assert profile.signal_source_mode == "INTERNAL"
    assert profile.execution_mode == "SIMULATION"
