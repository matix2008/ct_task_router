"""
main.py — точка входа для запуска FastAPI-приложения
"""

from urllib.parse import urlparse, urlunparse
from fastapi import FastAPI, HTTPException
from redis import Redis
from loguru import logger
import hvac

from app.queue.redis_queue import RedisQueue
from app.auth.security import VaultClient
from app.api.task_router import TaskRouter
from app.config.loader import get_config, get_secrets
from app.logs.setup import setup_logging


def create_app() -> FastAPI:
    """
    Создаёт и настраивает FastAPI-приложение.
    Загружает конфигурацию и секреты (для совместимости с uvicorn --factory).
    """
    logger.info("Инициализация приложения CT Task Router API")
    # Настройка логирования
    setup_logging()

    # Создание FastAPI приложения
    logger.debug("Создание FastAPI приложения")
    app = FastAPI(
        title="CT Task Router API",
        description="REST API для постановки задач в очередь",
        version="1.0.0"
    )

    try:
        config = get_config()
        secrets = get_secrets()
    except Exception as e:
        logger.exception("Ошибка загрузки конфигурации или секретов")
        raise RuntimeError("Ошибка инициализации приложения") from e

    try:
        # Redis
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
    except Exception as e:
        logger.exception("Ошибка подключения к Redis")
        raise RuntimeError("Ошибка подключения к Redis") from e

    try:
        # Vault
        vault_url = config["vault"]["url"].rstrip("/")
        auth_path = config["vault"].get("auth_path", "auth/jwt").rstrip("/")
        vault_token = secrets["vault"]["token"]

        client = hvac.Client(url=vault_url, token=vault_token)
        if not client.is_authenticated():
            logger.error("Не удалось аутентифицироваться в Vault с предоставленным токеном")
            raise HTTPException(status_code=401, detail="Vault authentication failed")

        vault_client = VaultClient(client=client, vault_url = vault_url, auth_path=auth_path)
    except HTTPException as e:
        raise   # Не перехватываем свои же исключения
    except Exception as e:
        logger.exception("Ошибка подключения к Vault")
        raise RuntimeError("Ошибка подключения к Vault") from e

    task_router = TaskRouter(redis_queue=redis_queue, vault_client=vault_client)
    app.include_router(task_router)
    return app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:create_app", host="0.0.0.0", port=8000, factory=True)
