"""
Модуль загрузки и валидации конфигурации и секретов из файлов.

- Конфигурация валидируется по JSON-схеме.
- Secrets не валидируются, но могут использоваться в Vault-клиенте и других частях системы.
"""

import json
import os
from functools import lru_cache
from jsonschema import validate, ValidationError


# Пути к конфигурации и схеме
CONFIG_PATH = "config.json"
SECRETS_PATH = ".secrets.json"
SCHEMA_PATH = "config/schema.json"


@lru_cache()
def get_config() -> dict:
    """
    Загружает и валидирует конфигурационный файл.

    :raises RuntimeError: при ошибке валидации или чтении файлов
    :return: Словарь с валидной конфигурацией
    """
    if not os.path.exists(CONFIG_PATH):
        raise RuntimeError(f"Файл конфигурации не найден: {CONFIG_PATH}")

    if not os.path.exists(SCHEMA_PATH):
        raise RuntimeError(f"Файл схемы не найден: {SCHEMA_PATH}")

    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки конфигурации: {e}") from e

    try:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки схемы: {e}") from e

    try:
        validate(config, schema)
    except ValidationError as e:
        path = " → ".join([str(p) for p in e.path])
        raise RuntimeError(f"Ошибка валидации конфигурации: {e.message} (поле: {path})") from e

    return config


@lru_cache()
def get_secrets() -> dict:
    """
    Загружает secrets из .secrets.json.

    :raises RuntimeError: при ошибке чтения
    :return: Словарь с секретами
    """
    if not os.path.exists(SECRETS_PATH):
        raise RuntimeError(f"Файл секретов не найден: {SECRETS_PATH}")

    try:
        with open(SECRETS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки секретов: {e}") from e
