# tests/test_redis_queue.py

"""
Unit-тесты для RedisQueue.
Проверяются сценарии сохранения, извлечения, обновления и работы с очередями Redis.
"""

from uuid import uuid4
import json
import pytest
from app.queue.redis_queue import RedisQueue
from app.api.models import TaskStatus, TaskType


def test_save_task_sets_data_and_ttl(mock_redis):
    """Проверка: задача сохраняется с TTL по умолчанию."""
    queue = RedisQueue(client=mock_redis)
    task_id = uuid4()
    data = {"uuid": str(task_id), "type": "calc_hash", "status": "created"}
    queue.save_task(task_id, data)

    mock_redis.hset.assert_called_once()
    mock_redis.expire.assert_called_once()


def test_save_task_with_custom_ttl(mock_redis):
    """Проверка: TTL можно задать вручную."""
    queue = RedisQueue(client=mock_redis)
    task_id = uuid4()
    queue.save_task(task_id, {"status": "created"}, ttl_seconds=100)
    mock_redis.expire.assert_called_once_with(f"task:{task_id}", 100)


def test_get_task_found(mock_redis):
    """Проверка: задача найдена и десериализована как TaskInfo."""
    task_id = uuid4()
    mock_redis.hgetall.return_value = {
        b"uuid": json.dumps(str(task_id)).encode(),
        b"type": json.dumps(TaskType.CALC_HASH.value).encode(),
        b"status": json.dumps(TaskStatus.DONE.value).encode(),
        b"code": json.dumps(0).encode(),
        b"message": json.dumps("OK").encode()
    }
    queue = RedisQueue(client=mock_redis)
    task = queue.get_task(task_id)

    assert task.uuid == task_id
    assert task.status == TaskStatus.DONE
    assert task.code == 0
    assert task.message == "OK"


def test_get_task_not_found(mock_redis):
    """Проверка: Redis возвращает пустой ответ — задача не найдена."""
    mock_redis.hgetall.return_value = {}
    queue = RedisQueue(client=mock_redis)
    task = queue.get_task(uuid4())
    assert task is None


def test_get_task_invalid_data(mock_redis):
    """Проверка: данные в Redis невалидны для TaskInfo — выбрасывается исключение."""
    task_id = uuid4()
    mock_redis.hgetall.return_value = {
        b"uuid": b"not-a-uuid",
        b"type": b'"unknown_task_type"',
        b"status": b'"done"'
    }
    queue = RedisQueue(client=mock_redis)
    with pytest.raises(ValueError):
        queue.get_task(task_id)


def test_update_task(mock_redis):
    """Проверка: обновление задачи вызывает hset с правильным mapping."""
    queue = RedisQueue(client=mock_redis)
    queue.update_task(uuid4(), {"status": "done"})
    mock_redis.hset.assert_called_once()


def test_update_task_multiple_fields(mock_redis):
    """Проверка: обновление нескольких полей сериализуется корректно."""
    queue = RedisQueue(client=mock_redis)
    task_id = uuid4()
    updates = {"status": "done", "message": "OK", "code": 0}
    queue.update_task(task_id, updates)
    mock_redis.hset.assert_called_once()
    _, kwargs = mock_redis.hset.call_args
    assert "mapping" in kwargs
    assert json.loads(kwargs["mapping"]["status"]) == "done"


def test_enqueue(mock_redis):
    """Проверка: UUID задачи помещается в очередь Redis."""
    queue = RedisQueue(client=mock_redis)
    task_id = uuid4()
    queue.enqueue("queue_in", task_id)
    mock_redis.lpush.assert_called_once_with("queue_in", task_id)


def test_dequeue_returns_uuid(mock_redis):
    """Проверка: brpop возвращает UUID задачи в виде строки."""
    queue = RedisQueue(client=mock_redis)
    mock_redis.brpop.return_value = ("queue", b"uuid-123")
    uuid = queue.dequeue("queue")
    assert uuid == "uuid-123"


def test_dequeue_empty_queue_returns_none(mock_redis):
    """Проверка: пустая очередь возвращает None."""
    queue = RedisQueue(client=mock_redis)
    mock_redis.brpop.return_value = None
    uuid = queue.dequeue("queue")
    assert uuid is None
