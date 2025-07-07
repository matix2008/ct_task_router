# tests/test_task_router.py

"""
Тесты для TaskRouter: проверка отправки задач, получения информации и обработки ошибок.
"""
from uuid import uuid4
import pytest

from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.api.task_router import TaskRouter
from app.api.models import TaskInput, TaskType, TaskResponse



def test_submit_task_success(redis_queue, vault_client):
    """Успешная отправка задачи через endpoint /submit."""
    router = TaskRouter(redis_queue, vault_client)
    task_input = TaskInput(type=TaskType.CALC_HASH, upload={"filename": "file.txt"})
    response: TaskResponse = router.routes[0].endpoint(task_input, authorization="Bearer token")
    assert isinstance(response, TaskResponse)
    assert response.uuid is not None
    assert response.type == TaskType.CALC_HASH


def test_submit_task_invalid_data(redis_queue, vault_client):
    """Отправка некорректных данных через TestClient приводит к 422 Unprocessable Entity."""
    app = FastAPI()
    router = TaskRouter(redis_queue, vault_client)
    for route in router.routes:
        app.router.routes.append(route)

    client = TestClient(app)
    response = client.post("/submit", json={"invalid": "data"}, \
                           headers={"Authorization": "Bearer token"})
    assert response.status_code == 422


def test_submit_task_internal_error(redis_queue, vault_client):
    """Исключение при сохранении задачи в Redis оборачивается в HTTP 500."""
    redis_queue.save_task.side_effect = Exception("Redis error")

    router = TaskRouter(redis_queue, vault_client)
    sample_task = TaskInput(type=TaskType.CALC_HASH, upload={"key": "value"})
    with pytest.raises(HTTPException) as exc:
        router.routes[0].endpoint(sample_task, authorization="Bearer token")
    assert exc.value.status_code == 500
    assert "Internal server error" in str(exc.value.detail)


def test_task_info_not_found(redis_queue, vault_client):
    """Обращение к несуществующей задаче приводит к HTTP 400."""
    vault_client.authenticate_user.return_value = ("test_user", "test_role")
    redis_queue.get_task.return_value = None
    router = TaskRouter(redis_queue, vault_client)
    with pytest.raises(HTTPException) as exc:
        router.routes[1].endpoint(taskid=uuid4(), authorization="Bearer token")
    assert exc.value.status_code == 400
    assert "Invalid task ID" in str(exc.value.detail)


def test_task_info_success(redis_queue, vault_client):
    """Успешное получение информации о задаче по UUID."""
    task_uuid = uuid4()
    vault_client.authenticate_user.return_value = ("test_user", "test_role")
    redis_queue.get_task.return_value = {
        "uuid": str(task_uuid),
        "type": "calc_hash",
        "status": "done",
        "created": "2024-01-01T00:00:00+00:00",
        "ExternalId": "X123",
        "code": 0,
        "message": "OK",
        "result": {"hash": "abc123"}
    }
    router = TaskRouter(redis_queue, vault_client)
    response = router.routes[1].endpoint(taskid=task_uuid, authorization="Bearer ok")
    assert response.uuid == task_uuid
    assert response.type == TaskType.CALC_HASH
    assert response.status == "done"
    assert response.result["hash"] == "abc123"


def test_task_info_invalid_type_raises_valueerror(redis_queue, vault_client):
    """Некорректный тип задачи вызывает HTTP 400 с пояснением."""
    task_uuid = uuid4()
    vault_client.authenticate_user.return_value = ("test_user", "test_role")
    redis_queue.get_task.return_value = {
        "uuid": str(task_uuid),
        "type": "invalid_type",
        "status": "done",
        "created": "2024-01-01T00:00:00+00:00"
    }
    router = TaskRouter(redis_queue, vault_client)
    with pytest.raises(HTTPException) as exc:
        router.routes[1].endpoint(taskid=task_uuid, authorization="Bearer ok")
    assert exc.value.status_code == 400
    assert "Invalid task type" in str(exc.value.detail)


def test_health_check_returns_ok(redis_queue, vault_client):
    """Проверка доступности сервиса через endpoint /health с использованием TestClient."""
    app = FastAPI()
    router = TaskRouter(redis_queue, vault_client)
    for route in router.routes:
        app.router.routes.append(route)

    client = TestClient(app)
    response = client.post("/health")
    assert response.status_code == 200
    assert response.json() == {"code": 1, "message": "All right"}
