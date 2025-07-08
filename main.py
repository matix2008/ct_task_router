"""
main.py — точка входа для запуска FastAPI-приложения
"""

from urllib.parse import urlparse, urlunparse
import time
from fastapi import FastAPI, HTTPException
from redis import Redis
from loguru import logger
import hvac


from app.queue.redis_queue import RedisQueue
from app.auth.security import VaultClient
from app.api.task_router import TaskRouter
from app.config.loader import get_config, get_secrets
from app.logging.setup import setup_logging

VAULT_CONNECTION_DELAY = 3  # Задержка для корректной инициализации Vault

def create_app() -> FastAPI:
    """
    Создаёт и настраивает FastAPI-приложение.
    Загружает конфигурацию и секреты (для совместимости с uvicorn --factory).
    """
    logger.info("CT Task Router initialization started")

    app = None  # Инициализация переменной приложения
    config = None  # Инициализация переменной конфигурации
    secrets = None  # Инициализация переменной секретов

    try:
        # Загрузка конфигурации и секретов
        config = get_config()
        secrets = get_secrets()

        # Настройка логирования
        setup_logging(full_config=config)

        # Создание FastAPI приложения
        logger.debug("FastAPI application is being created")
        app = FastAPI(
            title="CT Task Router API",
            description="REST API для постановки задач в очередь",
            version="1.0.0"
        )

        logger.debug("FastAPI application was successfully created!")
    except Exception as e:
        logger.exception("Configuration or secrets loading failed")
        raise RuntimeError("Application initialization error") from e

    try:
        # Redis
        logger.debug("Redis client is being created")
        redis_url = config["queue"]["url"]
        redis_password = secrets.get("redis", {}).get("password")

        if redis_password:
            parsed_url = urlparse(redis_url)
            netloc = f":{redis_password}@{parsed_url.hostname}"
            if parsed_url.port:
                netloc += f":{parsed_url.port}"
            redis_url_with_auth = urlunparse(parsed_url._replace(netloc=netloc))
        else:
            redis_url_with_auth = redis_url

        redis_client = Redis.from_url(redis_url_with_auth)
        if not redis_client.ping():
            raise ConnectionError("Redis не отвечает на ping")

        redis_queue = RedisQueue(client=redis_client)

        logger.debug("Redis client was successfully created!")
    except Exception as e:
        logger.exception("Redis connection error")
        raise RuntimeError("Redis connection error") from e

    try:
        # Vault
        logger.debug("Vault client is being created")
        vault_url = config["vault"]["url"].rstrip("/")
        auth_path = config["vault"].get("auth_path", "auth/jwt").rstrip("/")
        vault_token = secrets["vault"]["token"]

        time.sleep(VAULT_CONNECTION_DELAY)  # Задержка для корректной инициализации Vault

        client = hvac.Client(url=vault_url, token=vault_token)
        if not client.is_authenticated():
            logger.error("Failed to authenticate with Vault using the provided token")
            raise HTTPException(status_code=401, detail="Vault authentication failed")

        vault_client = VaultClient(client=client, vault_url = vault_url, auth_path=auth_path)

        logger.debug("Vault client was successfully created!")
    except HTTPException as e:
        raise   # Не перехватываем свои же исключения
    except Exception as e:
        logger.exception("Vault connection error")
        raise RuntimeError("Vault connection error") from e

    try:
        logger.debug("TaskRouter is being initialized")
        # Инициализация маршрутизатора задач с Redis и Vault клиентами
        task_router = TaskRouter(redis_queue=redis_queue, vault_client=vault_client)
        app.include_router(task_router)
        logger.debug("TaskRouter was successfully initialized!")
        return app
    except Exception as e:
        logger.exception("TaskRouter initialization error")
        raise RuntimeError("TaskRouter initialization error") from e

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:create_app", host="0.0.0.0", port=8000, factory=True)
