"""
Обёртка над Redis-клиентом для работы с задачами и очередями.
Обеспечивает сохранение задач, обновление, извлечение и работу с очередями.
"""

import json
from uuid import UUID
from typing import Optional
import redis
from loguru import logger
from app.api.models import TaskInfo

class RedisQueue:
    """
    Класс-обёртка для взаимодействия с Redis как с брокером задач и хранилищем состояний.
    """

    def __init__(self, client: redis.Redis, default_ttl: int = 3600):
        """
        Инициализация очереди.

        :param client: Подключённый Redis клиент
        :param default_ttl: TTL (в секундах) для хранения задач
        """
        self.client = client
        self.default_ttl = default_ttl

    def save_task(self, task_uuid: UUID, data: dict, ttl_seconds: Optional[int] = None) -> None:
        """
        Сохраняет задачу в Redis Hash и устанавливает TTL.

        :param task_uuid: Идентификатор задачи
        :param data: Данные задачи
        :param ttl_seconds: Время жизни задачи в секундах
        """
        key = f"task:{task_uuid}" # ключ для хранения задачи
        # сохраняем данные задачи в виде JSON
        self.client.hset(key, mapping={k: json.dumps(v) for k, v in data.items()})
        # устанавливаем время жизни задачи
        self.client.expire(key, ttl_seconds or self.default_ttl)

        logger.debug(f"Задача {task_uuid} сохранена с TTL {ttl_seconds or self.default_ttl} секунд")

    def get_task(self, task_uuid: UUID) -> Optional[dict]:
        """
        Извлекает задачу по UUID.

        :param task_uuid: Идентификатор задачи
        :return: Словарь с данными задачи или None
        """
        key = f"task:{task_uuid}" # ключ для хранения задачи
        # читаем (не удаляя) данные задачи из Redis Hash
        raw = self.client.hgetall(key)
        if not raw:
            logger.warning(f"Задача {task_uuid} не найдена в Redis")
            return None
        logger.debug(f"Задача {task_uuid} извлечена")
        # было return {k.decode(): json.loads(v) for k, v in raw.items()}
        return TaskInfo.model_validate({k.decode(): json.loads(v) for k, v in raw.items()})


    def update_task(self, task_uuid: UUID, updates: dict) -> None:
        """
        Обновляет поля задачи в Redis.

        :param task_uuid: Идентификатор задачи
        :param updates: Поля для обновления
        """
        key = f"task:{task_uuid}"
        self.client.hset(key, mapping={k: json.dumps(v) for k, v in updates.items()})
        logger.debug(f"Задача {task_uuid} обновлена полями: {list(updates.keys())}")

    def enqueue(self, queue_name: str, task_uuid: UUID) -> None:
        """
        Помещает UUID задачи в указанную очередь Redis.

        :param queue_name: Имя очереди
        :param task_uuid: Идентификатор задачи
        """
        self.client.lpush(queue_name, task_uuid)
        logger.debug(f"Задача {task_uuid} помещена в очередь {queue_name}")

    def dequeue(self, queue_name: str, timeout: int = 0) -> Optional[str]:
        """
        Блокирующее извлечение UUID задачи из очереди.

        :param queue_name: Имя очереди
        :param timeout: Таймаут ожидания (0 = бесконечно)
        :return: UUID задачи или None
        """
        result = self.client.brpop(queue_name, timeout=timeout)
        if result:
            task_uuid = result[1].decode()
            logger.debug(f"Задача {task_uuid} извлечена из очереди {queue_name}")
            return task_uuid
        return None
