"""Safe, explicit loader for the optional untracked local YAML configuration."""

from copy import deepcopy
from pathlib import Path

import yaml


DEFAULT_LOCAL_CONFIG = {
    "telegram": {
        "api_id": 0,
        "api_hash": "",
        "phone": "",
        "session": "",
    },
    "trading": {
        "risk_percent": 0,
        "tp_level": 1,
        "execute_market": False,
    },
}


class LocalConfigError(ValueError):
    """Raised when an existing local configuration cannot be loaded safely."""


def load_local_config(path=None):
    """Load an existing local config without creating files or starting services."""

    config_path = Path(path) if path is not None else (
        Path(__file__).resolve().parent.parent / "config.yaml"
    )
    if not config_path.exists():
        return deepcopy(DEFAULT_LOCAL_CONFIG)

    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise LocalConfigError(
            f"No se pudo cargar la configuración local: {config_path.name}"
        ) from error

    if loaded is None:
        return deepcopy(DEFAULT_LOCAL_CONFIG)
    if not isinstance(loaded, dict):
        raise LocalConfigError(
            f"La configuración local debe ser un objeto YAML: {config_path.name}"
        )
    return loaded
