"""
Модуль авторизации пользователей с помощью JWT или Basic, сверяясь с Vault.

Vault настраивается как внутренний механизм аутентификации клиентов 
(через JWT и логин/пароль), с использованием:
- одной универсальной JWT-роли (dynamic);
- метаданных токена для определения прав клиента;
- userpass для сервисов без поддержки JWT.
"""

import base64
import hvac
from fastapi import HTTPException
from loguru import logger

class VaultClient:
    """
    Клиент для проверки авторизации через Vault.

    Поддерживает:
    - JWT-токены (через endpoint Vault)
    - Basic-аутентификацию (через KV хранилище Vault)

    Exceptions:
    - 401, Missing credentials
    - 401, Authentication failed
    - 403, Not allowed
    - 400, Client ID or Role not found in Vault response metadata
    """

    def __init__(self, client: hvac.Client, vault_url: str, auth_path: str):
        """
        Инициализирует клиента Vault с явными параметрами.

        :param client: экземпляр Vault-сервера
        :param vault_url: URL Vault-сервера (например, "http://localhost:8200")
        :param auth_path: Путь для JWT аутентификации (по умолчанию "auth/jwt")
        """
        self.client = client
        self.vault_url = vault_url
        self.auth_path = auth_path

        # Аутентификация в Vault не нужна -> client.auth.jwt.login(mount_point=auth_path)

    def authenticate_user(self, authorization: str, action: str) -> tuple:
        """
        Проверяет заголовок авторизации и возвращает имя пользователя.

        :param authorization: Строка из HTTP-заголовка Authorization
        :return: Имя пользователя, если аутентификация успешна
        :raises HTTPException: 401 при ошибке
        """
        try:
            if authorization.startswith("Bearer "):
                jwt_token = authorization.split(" ", 1)[1]
                return self.verify_jwt(jwt_token, action)
            elif authorization.startswith("Basic "):
                credentials = base64.b64decode(authorization.split(" ", 1)[1]).decode()
                username, password = credentials.split(":", 1)
                return self.verify_basic(username, password, action)
            else:
                logger.warning("Missing credentials")
                raise HTTPException(status_code=401, detail="Missing credentials")
        except HTTPException:
            raise  # Необрабатываем собственные ошибки, чтобы не скрывать их
        except Exception as e:
            raise HTTPException(status_code=401, detail="Authentication failed") from e

    def verify_jwt(self, token: str, action: str) -> tuple:
        """
        Проверяет JWT через Vault и возвращает имя пользователя из метаданных.

        :param token: JWT, полученный от клиента.
        :param action: Действие, которое нужно проверить (например, "calc_hash", "water_marks").
        :return: Имя пользователя, извлечённое из метаданных Vault.
        :raises ValueError: если аутентификация не удалась или нет метаданных.
        """
        client_id = "<unknown>"
        role = "<unknown>"
        try:
            # Проверяем JWT-токен через Vault
            auth_info = self.client.auth.jwt_login(jwt=token, role="dynamic")
            # Извлекаем client_id и роль из метаданных и проверяем права
            client_id, role = self._verify(auth_info, action)

            # Возвращаем client_id и роль
            logger.debug(f"JWT-аутентификация успешна для client_id {client_id} с ролью {role}")
            return client_id, role

        except Exception as e:
            logger.warning(f"Ошибка аутентификации клиента {client_id} с JWT: {str(e)}")
            raise e

    def verify_basic(self, username: str, password: str, action: str) -> tuple:
        """
        Проверяет логин и пароль через KV-хранилище Vault.

        :param username: Имя пользователя
        :param password: Пароль
        :param action: Действие, которое нужно проверить (например, "calc_hash", "water_marks")
        :return: Имя пользователя при успехе
        :raises HTTPException: 401 при ошибке аутентификации
        """
        client_id = "<unknown>"
        role = "<unknown>"
        try:
            #result = self.client.secrets.kv.v2.read_secret_version(path=f"users/{username}")
            #stored_password = result["data"]["data"]["password"]
            #
            #if not hmac.compare_digest(password, stored_password):
            #    logger.warning(f"Неверный пароль для пользователя {username}")
            #    raise HTTPException(status_code=401, detail="Invalid password")

            # Выполняем аутентификацию через userpass
            # (предполагается, что userpass настроен в Vault)
            auth_info = self.client.userpass_login(username=username, password=password)
            # Извлекаем client_id и роль из метаданных и проверяем права
            client_id, role = self._verify(auth_info, action)

            logger.debug(f"Basic-аутентификация успешна для пользователя \
                         {client_id} с ролью {role}")
            return client_id, role

        except Exception as e:
            logger.warning(f"Ошибка аутентификации клиента {client_id} с Basic: {str(e)}")
            raise e

    def _verify(self, auth_info, action) -> tuple:
        """
        Вспомогательный метод для проверки аутентификации.

        :param auth_info: Информация о пользователе из Vault
        :return: Кортеж с client_id и ролью
        """

        # Извлекаем метаданные из ответа Vault
        role = auth_info["metadata"].get("role")
        client_id = auth_info["metadata"].get("client_id")

        # Проверяем, что client_id присутствует в метаданных
        if not client_id or not role:
            logger.error("Client ID or Role not found in Vault response metadata.")
            raise HTTPException(status_code=400, \
                                detail="Client ID or Role not found in Vault response metadata.")

        # Проверяем права клиента на выполнение действия
        if not self.is_authorized(role, action):
            logger.error(f"Client {client_id} with role \
                         {role} is not allowed to perform action '{action}'")
            raise HTTPException(status_code=403, detail="Not allowed")

        return client_id, role

    def is_authorized(self, role: str, action: str) -> bool:
        """
        Проверяет, имеет ли пользователь право на выполнение действия.
        :param role: Роль пользователя (например, "admin", "service", "copytrust_site")
        :param action: Действие, которое нужно проверить (например, "calc_hash", "water_marks")
        :return: True, если действие разрешено для роли, иначе False
        """
        return {
            "admin": lambda: True,
            "service": lambda: action in ["calc_hash", "water_marks"],
            "copytrust_site": lambda: action == "calc_hash"
        }.get(role, lambda: False)()
