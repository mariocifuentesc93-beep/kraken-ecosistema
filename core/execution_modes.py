from enum import Enum


class ExecutionMode(Enum):
    OFF = "OFF"
    SIMULATION = "SIMULATION"
    PAPER = "PAPER"
    DEMO = "DEMO"
    LIVE = "LIVE"


def get_execution_modes():
    return [mode.value for mode in ExecutionMode]


def is_valid_execution_mode(mode):
    if mode is None:
        return False

    return str(mode).upper() in get_execution_modes()
