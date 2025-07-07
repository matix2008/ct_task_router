# tests/test_loader.py

"""
Unit-тесты для модуля загрузки конфигурации и секретов.
Проверяется поведение при корректных и ошибочных конфигурациях:
- Успешная загрузка конфигурации и секретов
- Ошибки: отсутствующие файлы, невалидный JSON, ошибка валидации
- Защита от кэширования через @lru_cache
"""

import json
import pytest
from app.config import loader


@pytest.fixture(name="valid_config_file")
def valid_config_file_fixture(tmp_path):
    """
    Создаёт временные config.json и schema.json со всеми обязательными полями.
    Обновляет пути CONFIG_PATH и SCHEMA_PATH в модуле loader.
    Возвращает tuple (config: dict, schema: dict)
    """
    config_path = tmp_path / "config.json"
    schema_path = tmp_path / "schema.json"

    config = {
        "vault": {"url": "http://vault:8200"},
        "queue": {"type": "redis", "url": "redis://localhost:6379"},
        "logging": {
            "level": "INFO",
            "log_file": "app.log",
            "rotation": {"when": "1 day", "backupCount": 7}
        }
    }

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["queue", "vault", "logging"],
        "properties": {
            "vault": {
                "type": "object",
                "required": ["url"],
                "properties": {"url": {"type": "string", "format": "uri"}},
                "additionalProperties": False
            },
            "queue": {
                "type": "object",
                "required": ["type", "url"],
                "properties": {
                    "type": {"type": "string"},
                    "url": {"type": "string"}
                },
                "additionalProperties": False
            },
            "logging": {
                "type": "object",
                "required": ["level", "log_file", "rotation"],
                "properties": {
                    "level": {"type": "string"},
                    "log_file": {"type": "string"},
                    "rotation": {
                        "type": "object",
                        "required": ["when", "backupCount"],
                        "properties": {
                            "when": {"type": "string"},
                            "backupCount": {"type": "integer", "minimum": 1}
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }

    config_path.write_text(json.dumps(config), encoding="utf-8")
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    loader.CONFIG_PATH = str(config_path)
    loader.SCHEMA_PATH = str(schema_path)
    loader.get_config.cache_clear()

    return config, schema


def test_get_config_success(valid_config_file):
    """Успешная загрузка валидной конфигурации"""
    result = loader.get_config()
    assert result["vault"]["url"] == "http://vault:8200"


def test_get_config_missing_file(tmp_path):
    """Ошибка: config.json отсутствует"""
    loader.CONFIG_PATH = str(tmp_path / "missing.json")
    loader.SCHEMA_PATH = str(tmp_path / "schema.json")
    loader.get_config.cache_clear()
    with pytest.raises(RuntimeError, match="Configuration file not found"):
        loader.get_config()


def test_get_config_invalid_json(tmp_path):
    """Ошибка: config.json содержит невалидный JSON"""
    config_file = tmp_path / "config.json"
    schema_file = tmp_path / "schema.json"
    config_file.write_text("{invalid_json}", encoding="utf-8")
    schema_file.write_text("{}", encoding="utf-8")

    loader.CONFIG_PATH = str(config_file)
    loader.SCHEMA_PATH = str(schema_file)
    loader.get_config.cache_clear()

    with pytest.raises(RuntimeError, match="Error loading configuration"):
        loader.get_config()


def test_get_config_invalid_schema_json(tmp_path):
    """Ошибка: schema.json содержит невалидный JSON"""
    config = tmp_path / "config.json"
    schema = tmp_path / "schema.json"

    config.write_text(json.dumps({
        "vault": {"url": "http://vault:8200"},
        "queue": {"type": "redis", "url": "redis://localhost:6379"},
        "logging": {
            "level": "INFO",
            "log_file": "app.log",
            "rotation": {"when": "1 day", "backupCount": 7}
        }
    }), encoding="utf-8")

    schema.write_text("{not_json}", encoding="utf-8")

    loader.CONFIG_PATH = str(config)
    loader.SCHEMA_PATH = str(schema)
    loader.get_config.cache_clear()

    with pytest.raises(RuntimeError, match="Error loading schema"):
        loader.get_config()


def test_get_config_validation_error(tmp_path, valid_config_file):
    """Ошибка: конфигурация не проходит валидацию по схеме"""
    _, schema = valid_config_file
    config = tmp_path / "config.json"
    schema_path = tmp_path / "schema.json"

    config.write_text(json.dumps({
        "vault": {},  # пропущено обязательное поле 'url'
        "queue": {"type": "redis", "url": "redis://localhost:6379"},
        "logging": {
            "level": "INFO",
            "log_file": "app.log",
            "rotation": {"when": "1 day", "backupCount": 7}
        }
    }), encoding="utf-8")

    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    loader.CONFIG_PATH = str(config)
    loader.SCHEMA_PATH = str(schema_path)
    loader.get_config.cache_clear()

    with pytest.raises(RuntimeError, match="Configuration validation error"):
        loader.get_config()


def test_get_secrets_success(tmp_path):
    """Успешная загрузка secrets из .secrets.json"""
    secrets_file = tmp_path / ".secrets.json"
    secrets_file.write_text(json.dumps({"redis": {"password": "secret"}}), encoding="utf-8")

    loader.SECRETS_PATH = str(secrets_file)
    loader.get_secrets.cache_clear()

    result = loader.get_secrets()
    assert result["redis"]["password"] == "secret"


def test_get_secrets_missing(tmp_path):
    """Ошибка: .secrets.json отсутствует"""
    loader.SECRETS_PATH = str(tmp_path / "notfound.json")
    loader.get_secrets.cache_clear()

    with pytest.raises(RuntimeError, match="Secrets file not found"):
        loader.get_secrets()


def test_get_secrets_invalid_json(tmp_path):
    """Ошибка: .secrets.json содержит невалидный JSON"""
    secrets = tmp_path / ".secrets.json"
    secrets.write_text("{bad_json}", encoding="utf-8")

    loader.SECRETS_PATH = str(secrets)
    loader.get_secrets.cache_clear()

    with pytest.raises(RuntimeError, match="Error loading secrets"):
        loader.get_secrets()
