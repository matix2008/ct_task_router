"""
Маршрутизатор задач CT Task Router с явной инициализацией зависимостей.
Объединяет доступ к Redis и Vault, предоставляет REST-методы для работы с задачами.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
import inspect
from fastapi import APIRouter, HTTPException, Header
from loguru import logger

from app.api.models import TaskInput, TaskResponse, TaskInfo
from app.api.models import ErrorResponse, TaskType
from app.auth.security import VaultClient
from app.queue.redis_queue import RedisQueue


class TaskRouter(APIRouter):
    """
    Расширенный маршрутизатор задач для FastAPI-приложения.
    Реализует отправку задач, получение статуса задачи и проверку состояния сервиса.
    """

    def __init__(self, redis_queue: RedisQueue, vault_client: VaultClient):
        """
        Инициализация маршрутизатора с передачей зависимостей.

        :param redis_queue: Класс работы с Redis очередью и задачами
        :param vault_client: Клиент Vault для аутентификации
        """
        super().__init__()
        self.queue = redis_queue
        self.vault = vault_client
        self._add_routes()

    def who_called_me(self) -> str:
        """ Определяет имя вызывающей функции. """
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        caller_name = caller_frame.f_code.co_name
        return caller_name

    def _add_routes(self) -> None:
        """
        Регистрирует маршруты на объекте APIRouter.
        """

        @self.post("/submit", response_model=TaskResponse, responses={
            400: {"model": ErrorResponse},
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            500: {"model": ErrorResponse}
        })
        def submit_task(task: TaskInput, authorization: str = Header(...)) -> TaskResponse:
            """
            Принять задачу, проверить авторизацию и отправить в очередь.

            :param task: Входная задача от клиента
            :param authorization: JWT или Basic заголовок
            :return: Ответ с UUID задачи
            """
            auth_info = self.vault.authenticate_user(authorization, action=self.who_called_me())
            logger.info(f"Received task of type '{task.type}' \
                        from user '{auth_info[0]}' with role '{auth_info[1]}'")

            try:
                # Извлекаем данные задачи
                data = task.model_dump()

                task_uuid = str(uuid4()) # Генерируем новый UUID для задачи
                created_date = datetime.now(timezone.utc).isoformat()  # ISO 8601 формат

                data["uuid"] = task_uuid
                data["status"] = "created" # Начальный статус задачи
                data["created"] = created_date

                self.queue.save_task(task_uuid, data)
                self.queue.enqueue(f"{task.type.value}_INPUT", task_uuid)

                logger.debug(f"Task {task_uuid}/{task.ExternalId} \
                             enqueued to {task.type.value}_INPUT")

                return TaskResponse(
                    ExternalId=task.ExternalId,
                    type=task.type,
                    uuid=task_uuid,
                    created = created_date
                )
            except ValueError as ve:
                logger.error(f"Task validation error: {ve}")
                raise HTTPException(status_code=400, detail=str(ve)) from ve
            except Exception as e:
                logger.exception("Error while processing submit")
                raise HTTPException(status_code=500, detail="Internal server error") from e

        @self.get("/taskinfo", response_model=TaskInfo, responses={
            400: {"model": ErrorResponse},
            401: {"model": ErrorResponse},
            500: {"model": ErrorResponse}
        })
        def task_info(taskid: UUID, authorization: str = Header(...)) -> TaskInfo:
            """
            Получить информацию по задаче по UUID.

            :param taskid: UUID задачи
            :param authorization: JWT или Basic заголовок
            :return: Статус задачи и результат
            """

            # Проверяем авторизацию пользователя
            # и получаем информацию о нём
            auth_info = self.vault.authenticate_user(authorization, action=self.who_called_me())
            logger.debug(f"User '{auth_info[0]}' \
                         with role '{auth_info[1]}' requests status for task {taskid}")

            try:
                # Извлекаем задачу из очереди по UUID
                task_data = self.queue.get_task(taskid)
                if not task_data:
                    raise HTTPException(status_code=400, detail="Invalid task ID")

                return TaskInfo(
                    ExternalId=task_data.get("ExternalId"),
                    uuid=task_data["uuid"],
                    type=TaskType(task_data["type"]),
                    status=task_data["status"],
                    created=task_data["created"],
                    processed=task_data.get("processed"),
                    code=task_data.get("code"),
                    message=task_data.get("message"),
                    result=task_data.get("result")
                )
            except ValueError as ve:
                # Строго говоря, это ошибка обратной совместимости.
                # В обычной ситуации произойти не может.
                # Кто положил в очередь задачу и проверка типа прошла,
                # а потом список типов или статусов изменился
                # и когда мы вычитываем задачу, то не можем её обработать
                logger.error(f"Task validation error for {taskid} by type or status: {ve}")
                raise HTTPException(status_code=400, detail="Invalid task type") from ve
            except HTTPException as he:
                raise he  # Переправляем HTTP исключения без изменений
            except Exception as e:
                logger.exception("Error while processing task_info")
                raise HTTPException(status_code=500, detail="Internal server error") from e

        @self.post("/health", response_model=ErrorResponse, responses={
            500: {"model": ErrorResponse}
        })
        def health_check() -> ErrorResponse:
            """
            Проверка состояния сервиса.

            :return: Статус "жив/не жив"
            """
            try:
                return ErrorResponse(message="All right", code=1)
            except Exception as e:
                logger.exception("Health check error")
                raise HTTPException(status_code=500, detail={"message": str(e), "code": -1}) from e
