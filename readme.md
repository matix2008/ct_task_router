# 🧠 CT Task Router

Сервис маршрутизации и диспетчеризации задач с поддержкой JWT/BASIC аутентификации, REST API и Redis-очередей. Используется как интерфейс между внешними клиентами и обработчиками задач.

---

## 🚀 Возможности

* REST API для приёма задач и получения статуса
* Аутентификация через Vault (JWT / Basic)
* Валидация и сериализация задач (Pydantic)
* Отправка задач в очереди Redis (с TTL)
* Хранение статуса и результата в Redis
* Проверка состояния сервиса через `/health`
* Логгирование с ротацией файлов через Loguru
* Конфигурация и secrets валидируются по JSON-схеме

---

## 📁 Структура проекта

.
├── app/
│   ├── api/
│   │   ├── models.py         # Pydantic-схемы задач и ошибок
│   │   └── task_router.py    # Класс TaskRouter с маршрутами FastAPI
│   ├── auth/
│   │   └── security.py       # VaultClient: JWT/BASIC аутентификация
│   ├── config/
│   │   ├── loader.py         # Загрузка и валидация config.json и .secrets.json
│   │   └── schema.json       # JSON-схема для валидации конфигурации
|   ├── logs/
|   |   └── setup.py          # Настройка логирования Loguru
│   └── queue/
│       └── redis_queue.py    # RedisQueue: работа с Redis (hset/lpush/brpop)
├── tests/                    # Unit и интеграционные тесты
├── config.json               # Основной конфигурационный файл
├── .secrets.json             # Секреты доступа к Vault и Redis
├── main.py                   # Точка входа (создание и запуск FastAPI)
├── Dockerfile                # Сборка Docker-образа
├── docker-compose.yml        # Развёртывание с Redis и Vault
└── requirements.txt          # Зависимости проекта

---

## 🔧 Конфигурация

### config.json (валидируется по schema.json)

```json
{
  "vault": {
    "url": "http://127.0.0.1:8200",
    "auth_path": "auth/jwt"
  },
  "queue": {
    "type": "redis",
    "url": "redis://localhost:6379"
  },
  "logging": {
    "level": "DEBUG",
    "log_file": "./logs/ct_task_router.log",
    "rotation": {
      "when": "1 day",
      "backupCount": 7
    }
  }
}
```

### .secrets.json

```json
{
  "redis": {
    "username": "user",
    "password": "pass"
  },
  "vault": {
    "token": "vault-access-token"
  }
}
```

---

## 📫 REST API Методы

### `POST /submit`

* 🔐 Требует JWT или Basic авторизацию
* 📥 Вход: JSON с задачей (`ExternalId`, `type`, `upload`)
* 📤 Ответ: `uuid`, `created`, `type` + ошибки

### `GET /taskinfo?taskid={UUID}`

* 🔐 Требует авторизацию
* 📤 Ответ: `status`, `result`, `message`, `code`

### `POST /health`

* 📤 Ответ: `{ "message": "All right", "code": 1 }`

---

## 🧪 Тестирование

```bash
pytest --cov=app tests/
```

* `test_config.py` — загрузка конфигов
* `test_redis_queue.py` — Redis очередь
* `test_routes.py` — интеграция API
* `test_security.py` — проверка VaultClient

Все внешние зависимости мокируются.

---

## 🐳 Docker

```bash
docker-compose up --build
```

### Монтируются

* `./config.json` → `/config.json`
* `./.secrets.json` → `/.secrets.json`
* `./logs/` → `/logs/`

---

## 🔐 Vault Auth

* Поддержка `jwt` и `userpass`
* Роль JWT — `dynamic`, используется `metadata` (`client_id`, `role`)
* Авторизация по `role` и `action`, реализована в `security.py`
* Подробнее — см. `auth.md`

---

## 🧾 Vault: Инструкция администратора и схема работы сервера (v2)

### 📁 Часть 1. Инструкция администратора по конфигурированию Vault

**Назначение:** Настроить Vault как внутренний механизм аутентификации клиентов (через JWT и логин/пароль), с использованием:

* одной универсальной JWT-роли (`dynamic`);
* метаданных токена для определения прав клиента;
* userpass для сервисов без поддержки JWT.

**Шаги настройки:**

```bash
vault server -config=vault.hcl
vault operator init
vault operator unseal
vault login <root_token>

vault auth enable userpass
vault auth enable jwt

vault policy write noop-policy - <<EOF
path "*" {
  capabilities = []
}
EOF

vault write auth/userpass/users/service \
    password="strong_password" \
    policies="noop-policy" \
    metadata="client_id=client2,role=service"

vault write auth/jwt/config \
    oidc_discovery_url="http://127.0.0.1:8200/v1/identity/oidc" \
    bound_issuer="vault"

vault write auth/jwt/role/dynamic \
    role_type="jwt" \
    bound_subject="*" \
    user_claim="sub" \
    bound_issuer="vault" \
    metadata_claims="client_id,role" \
    policies="noop-policy" \
    ttl="1h"

vault write identity/oidc/token \
    subject="client3" \
    metadata="client_id=client3,role=admin" \
    policies="noop-policy" \
    ttl="3600"
```

**Пример JWT payload:**

```json
{
  "iss": "vault",
  "sub": "client1",
  "client_id": "client1",
  "role": "copytrust_site",
  "exp": 1718959200
}
```

---

### 🧩 Часть 2. Схема работы сервера при аутентификации и авторизации

```python
def authenticate_and_authorize(request):
    if request.jwt_token:
        auth_info = vault_client.jwt_login(jwt=request.jwt_token, role="dynamic")
    elif request.username and request.password:
        auth_info = vault_client.userpass_login(username=request.username, password=request.password)
    else:
        raise Unauthorized("Missing credentials")

    role = auth_info["metadata"].get("role")
    client_id = auth_info["metadata"].get("client_id")

    if not is_authorized(role, request.action):
        raise Forbidden("Not allowed")

    return proceed_with_action(client_id, role)
```

```python
def is_authorized(role: str, action: str) -> bool:
    return {
        "admin": lambda: True,
        "service": lambda: action in ["calc_hash", "water_marks"],
        "copytrust_site": lambda: action == "calc_hash"
    }.get(role, lambda: False)()
```

**Пример ответа Vault:**

```json
{
  "auth": {
    "client_token": "hvs.xxxxx",
    "entity_id": "...",
    "policies": ["noop-policy"],
    "metadata": {
      "client_id": "client1",
      "role": "copytrust_site"
    }
  }
}
```

---

## 📑 Форматы моделей (Pydantic)

### TaskInput

```json
{
  "ExternalId": "string (optional)",
  "type": "calc_hash | resize_image",
  "upload": { "any": "data" }
}
```

### TaskResponse

```json
{
  "ExternalId": "string",
  "type": "...",
  "uuid": "UUID",
  "created": "ISO8601"
}
```

### TaskInfo

```json
{
  "uuid": "UUID",
  "type": "...",
  "status": "created | pending | done | error",
  "created": "ISO8601",
  "processed": "ISO8601",
  "message": "string",
  "code": 0,
  "result": { "any": "data" }
}
```

### ErrorResponse

```json
{
  "code": 401,
  "message": "Unauthorized"
}
```

---

## 🛠️ Используемые технологии

* FastAPI / Pydantic v2
* Redis
* Vault
* Loguru (ротация логов)
* jsonschema
* pytest + coverage

---

## © COPYTRUST, 2025
