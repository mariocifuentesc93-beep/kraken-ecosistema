from enum import Enum


class RuntimeStatus(Enum):

    STOPPED = "STOPPED"

    STARTING = "STARTING"

    RUNNING = "RUNNING"

    PAUSED = "PAUSED"

    STOPPING = "STOPPING"

    ERROR = "ERROR"