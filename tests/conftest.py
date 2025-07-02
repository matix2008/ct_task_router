# tests/conftest.py

"""
Глобальные фикстуры для тестирования.
Мокаются Redis и Vault, создаются клиент и приложения FastAPI.
"""

from unittest.mock import MagicMock
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.queue.redis_queue as redis_queue_module
from app.queue.redis_queue import RedisQueue
from app.auth.security import VaultClient
from app.api.task_router import TaskRouter

@pytest.fixture(name="redis_queue")
def redis_queue_fixture():
    """Мок RedisQueue с возможностью задавать side_effect и return_value."""
    return MagicMock(spec=RedisQueue)

@pytest.fixture(name="vault_client")
def vault_client_fixture():
    """Мок VaultClient с полной имитацией поведения."""
    return MagicMock(spec=VaultClient)

@pytest.fixture(name="mock_redis")
def mock_redis_fixture(monkeypatch):
    """Мокаем redis.Redis и возвращаем поддельный экземпляр клиента Redis."""

    mock_instance = MagicMock()
    monkeypatch.setattr(redis_queue_module, "redis", MagicMock())
    redis_queue_module.redis.Redis.return_value = mock_instance
    return mock_instance

@pytest.fixture(name="test_client")
def test_client_fixture(mock_redis, vault_client):
    """
    Фикстура для запуска FastAPI с TaskRouter и замоканным Redis и VaultClient.
    Используется для интеграционного тестирования API.
    """
    app = FastAPI()
    router = TaskRouter(redis_queue=mock_redis, vault_client=vault_client)

    for route in router.routes:
        app.router.routes.append(route)

    return TestClient(app)
