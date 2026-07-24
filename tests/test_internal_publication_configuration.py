from types import SimpleNamespace

import pytest

from models.internal_publication_config import InternalPublicationConfig
from repositories.internal_publication_config_repository import (
    ACCOUNT_KEY,
    CHAT_KEY,
    DESTINATION_NAME_KEY,
    DESTINATION_TYPE_KEY,
    ENABLED_KEY,
    InternalPublicationConfigRepository,
)
from services.internal_publication_configuration_service import (
    InternalPublicationConfigurationService,
)


class MemorySettings:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def get_bool(self, key, default=False):
        value = self.get(key)
        if value is None:
            return default
        return str(value).lower() in {"1", "true", "yes", "on"}

    def set(self, key, value):
        self.values[key] = str(value)

    def remove(self, key):
        return self.values.pop(key, None) is not None


def test_global_configuration_round_trip():
    settings = MemorySettings()
    repository = InternalPublicationConfigRepository(settings)
    expected = InternalPublicationConfig(
        enabled=True,
        telegram_account_id=7,
        telegram_output_chat_id=-100123,
        destination_name="Señales Premium",
        destination_type="Canal",
    )

    repository.save(expected)

    assert repository.get() == expected
    assert settings.values == {
        ENABLED_KEY: "1",
        ACCOUNT_KEY: "7",
        CHAT_KEY: "-100123",
        DESTINATION_NAME_KEY: "Señales Premium",
        DESTINATION_TYPE_KEY: "Canal",
    }


def test_disabled_configuration_can_clear_destination():
    settings = MemorySettings()
    repository = InternalPublicationConfigRepository(settings)

    repository.save(InternalPublicationConfig())

    assert repository.get() == InternalPublicationConfig()
    assert ACCOUNT_KEY not in settings.values
    assert CHAT_KEY not in settings.values
    assert DESTINATION_NAME_KEY not in settings.values
    assert DESTINATION_TYPE_KEY not in settings.values


def configuration_service(repository, account=True, destinations=None):
    return InternalPublicationConfigurationService(
        repository=repository,
        account_provider=lambda account_id: (
            SimpleNamespace(id=account_id, enabled=True)
            if account
            else None
        ),
        destinations_provider=lambda account_id: (
            [{
                "chat_id": -100123,
                "title": "Señales Premium",
                "type": "Canal",
            }]
            if destinations is None
            else destinations
        ),
    )


def test_configuration_rejects_nonexistent_account():
    repository = InternalPublicationConfigRepository(MemorySettings())
    with pytest.raises(ValueError, match="cuenta"):
        configuration_service(repository, account=False).save(
            True,
            7,
            -100123,
        )


def test_configuration_rejects_nonexistent_chat():
    repository = InternalPublicationConfigRepository(MemorySettings())
    with pytest.raises(ValueError, match="chat"):
        configuration_service(
            repository,
            destinations=[],
        ).save(True, 7, -100123)


def test_global_configuration_is_disabled_by_default():
    repository = InternalPublicationConfigRepository(MemorySettings())

    assert repository.get() == InternalPublicationConfig()


def test_service_persists_destination_information():
    repository = InternalPublicationConfigRepository(MemorySettings())

    saved = configuration_service(repository).save(True, 7, -100123)

    assert saved.destination_name == "Señales Premium"
    assert saved.destination_type == "Canal"
    assert repository.get() == saved
