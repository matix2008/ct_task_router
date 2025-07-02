"""
Модели для API задач.
Определяют структуру входящих и исходящих данных.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class TaskType(str, Enum):
    """
    Перечисление допустимых типов задач.
    Добавляй новые типы задач по мере необходимости.
    """
    CALC_HASH = "calc_hash"
    RESIZE_IMAGE = "resize_image"

class TaskStatus(str, Enum):
    """
    Перечисление возможных статусов задачи.
    """
    CREATED = "created"
    PENDING = "pending"
    DONE = "done"
    ERROR = "error"


class TaskInput(BaseModel):
    """
    Модель входящей задачи.
    Содержит внешний идентификатор (опция), тип задачи и словарь параметров.
    """
    ExternalId: Optional[str] = None
    type: TaskType
    upload: Dict[str, Any]


class TaskResponse(BaseModel):
    """
    Ответ на постановку задачи в очередь.
    Содержит внешний идентификатор (опция), тип задачи, UUID и дату создания.
    """
    ExternalId: Optional[str] = None
    type: TaskType
    uuid: UUID
    created: datetime

    model_config = ConfigDict(ser_json_timedelta='iso8601')


class TaskInfo(BaseModel):
    """
    Статус задачи и результат обработки.
    Включает внешний идентификатор, UUID, тип, статус, метки времени, код и сообщение.
    """
    ExternalId: Optional[str] = None
    type: TaskType
    uuid: UUID
    status: TaskStatus  # created, pending, done, error
    created: Optional[datetime] = None
    processed: Optional[datetime] = None
    code: int
    message: str
    result: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(ser_json_timedelta='iso8601')


class ErrorResponse(BaseModel):
    """
    Модель ошибки в формате JSON.
    Содержит код и текст ошибки.
    """
    code: int
    message: str
