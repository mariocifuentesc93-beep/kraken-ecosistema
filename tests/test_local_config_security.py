import importlib
import sys
from pathlib import Path

import yaml

from config.local_config import DEFAULT_LOCAL_CONFIG, load_local_config


REQUIRED_STRUCTURE = {
    "telegram": {"api_id", "api_hash", "phone", "session"},
    "trading": {"risk_percent", "tp_level", "execute_market"},
}


def test_local_config_is_loaded_when_present(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        """
telegram:
  api_id: 123456
  api_hash: TEST_ONLY
  phone: "+0000000000"
  session: sessions/test
trading:
  risk_percent: 1
  tp_level: 2
  execute_market: false
""".strip(),
        encoding="utf-8",
    )

    loaded = load_local_config(path)

    assert loaded["telegram"]["api_hash"] == "TEST_ONLY"
    assert loaded["trading"]["execute_market"] is False


def test_missing_local_config_uses_safe_defaults_without_creating_file(tmp_path):
    missing = tmp_path / "config.yaml"

    loaded = load_local_config(missing)

    assert loaded == DEFAULT_LOCAL_CONFIG
    assert loaded["telegram"]["api_hash"] == ""
    assert loaded["telegram"]["phone"] == ""
    assert not missing.exists()


def test_example_config_contains_required_keys_and_only_placeholder_credentials():
    example_path = Path(__file__).resolve().parents[1] / "config.example.yaml"
    loaded = yaml.safe_load(example_path.read_text(encoding="utf-8"))

    for section, keys in REQUIRED_STRUCTURE.items():
        assert section in loaded
        assert keys <= set(loaded[section])

    assert loaded["telegram"]["api_hash"] == "REPLACE_ME"
    assert loaded["telegram"]["phone"] == "+0000000000"
    assert loaded["telegram"]["api_id"] == 123456


def test_importing_local_config_does_not_open_sqlite_or_connect_services(monkeypatch):
    forbidden = {"sqlite3", "MetaTrader5", "telethon"}
    previous = {name: sys.modules.pop(name, None) for name in forbidden}
    imported = []
    original_import = __import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".", 1)[0] in forbidden:
            imported.append(name)
            raise AssertionError(f"Importación externa no permitida: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", guarded_import)
    try:
        module = importlib.import_module("config.local_config")
        importlib.reload(module)
    finally:
        for name, value in previous.items():
            if value is not None:
                sys.modules[name] = value

    assert imported == []
