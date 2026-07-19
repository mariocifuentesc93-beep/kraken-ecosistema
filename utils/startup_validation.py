from importlib.util import find_spec
from pathlib import Path

import yaml

from database.database_manager import database_manager


REQUIRED_TABLES = {
    "profiles", "telegram_accounts", "mt5_accounts", "profile_mt5_accounts",
    "profile_telegram_channels", "symbols", "signals", "operations",
    "operation_events", "settings", "logs",
}


def validate_startup():
    """Return actionable startup errors without opening the main window."""
    errors = []
    try:
        database_manager.initialize()
        missing = sorted(table for table in REQUIRED_TABLES if not database_manager.table_exists(table))
        if missing:
            errors.append("Faltan tablas requeridas: " + ", ".join(missing))
    except Exception as error:
        errors.append(f"La base de datos no está disponible: {error}")

    config_path = Path(__file__).resolve().parent.parent / "config" / "app.yaml"
    try:
        with config_path.open(encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)
        if config is not None and not isinstance(config, dict):
            errors.append("El archivo config/app.yaml debe contener un objeto YAML.")
    except (OSError, yaml.YAMLError) as error:
        errors.append(f"No se pudo leer config/app.yaml: {error}")

    for module, label in (("MetaTrader5", "MetaTrader5"), ("telethon", "Telethon")):
        if find_spec(module) is None:
            errors.append(f"La dependencia requerida {label} no está instalada.")
    return errors
