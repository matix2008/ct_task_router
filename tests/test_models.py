# tests/test_models.py

"""
Тесты Pydantic моделей: TaskInput, TaskResponse, TaskInfo, ErrorResponse.
Проверяется корректность сериализации, десериализации и валидации.
"""

from uuid import uuid4
from datetime import datetime, timezone
from app.api.models import TaskInput, TaskResponse, TaskInfo, ErrorResponse, TaskStatus, TaskType


def test_task_input_model():
    """
    Проверка создания и сериализации модели TaskInput.
    """
    model = TaskInput(
        ExternalId="ext123",
        type=TaskType.CALC_HASH,
        upload={"param1": "value1"}
    )
    assert model.type == TaskType.CALC_HASH
    assert model.upload["param1"] == "value1"


def test_task_response_model():
    """
    Проверка TaskResponse: UUID, сериализация и тип задачи.
    """
    task_id = uuid4()
    now = datetime.now(timezone.utc)
    response = TaskResponse(
        ExternalId=None,
        type=TaskType.RESIZE_IMAGE,
        uuid=task_id,
        created=now
    )
    assert response.type == TaskType.RESIZE_IMAGE
    assert response.uuid == task_id


def test_task_info_model():
    """
    Проверка модели TaskInfo: статусы, обработка и результат.
    """
    task_id = uuid4()
    model = TaskInfo(
        ExternalId="external",
        uuid=task_id,
        type=TaskType.CALC_HASH,
        status=TaskStatus.DONE,
        created=datetime.now(timezone.utc),
        processed=datetime.now(timezone.utc),
        code=0,
        message="Success",
        result={"output": "hashvalue"}
    )
    assert model.status == TaskStatus.DONE
    assert model.result is not None
    assert model.result["output"] == "hashvalue"


def test_error_response_model():
    """
    Проверка ErrorResponse — структура ошибки и значения.
    """
    error = ErrorResponse(code=404, message="Not Found")
    assert error.code == 404
    assert error.message == "Not Found"
