# 🧠 CT Task Router

Сервис маршрутизации и диспетчеризации задач с поддержкой JWT/BASIC аутентификации, REST API и Redis-очередей. Используется как интерфейс между внешними клиентами и обработчиками задач.

---

## 🚀 Возможности

- Получение задач от клиентов через REST API
- Аутентификация через Vault (JWT / Basic)
- Валидация задач и маршрутизация в очередь Redis
- Получение информации о задаче по UUID
- Проверка состояния сервиса `/health`
- Логгирование с ротацией

---

## 📁 Структура проекта

```
.
├── app/
│   ├── api/
│   │   ├── models.py         # Pydantic-схемы JSON-TASK, JSON-ERROR и пр.
│   │   └── task_router.py    # Класс TaskRouter с маршрутами REST API
│   ├── auth/
│   │   └── security.py       # VaultClient, проверка JWT и Basic
│   ├── config/
│   │   └── loader.py         # Загрузка config.json и .secret.json с кешированием
│   └── queue/
│       └── redis_queue.py    # Работа с Redis: сохранение задач, очереди
├── tests/
│   ├── test_config.py        # Тесты загрузки конфигурации
│   ├── test_redis_queue.py   # Юнит-тесты RedisQueue (mocked)
│   ├── test_routes.py        # Интеграционные тесты REST API
│   └── test_security.py      # Юнит-тесты VaultClient
├── logs/                     # Логи (монтируется в Docker)
├── config.json               # Основной конфигурационный файл (монтируется)
├── .secret.json              # Vault и Redis доступ (монтируется)
├── main.py                   # Точка входа. Запуск FastAPI и маршрутов
├── Dockerfile                # Инструкция сборки контейнера
├── docker-compose.yml        # Конфигурация сервиса с монтированием конфигов
└── requirements.txt          # Зависимости проекта
```

---

## 🔧 Конфигурация

### config.json
```json
{
  "vault": { "url": "http://127.0.0.1:8200", "auth_path": "auth/jwt" },
  "queue": { "type": "redis", "url": "redis:6379" },
  "logging": {
    "level": "DEBUG",
    "log_file": "./logs/ct_task_router.log",
    "rotation": { "when": "midnight", "backupCount": 7 }
  }
}
```

### .secret.json
```json
{
  "redis": { "username": "user", "password": "pass" },
  "vault": { "token": "vault-access-token" }
}
```

---

## 🧪 Тестирование

### 📌 Запуск всех тестов
```bash
pytest --cov=app tests/
```

### 🧪 Структура тестов
- `test_config.py` — чтение и кеширование config/secret
- `test_redis_queue.py` — RedisQueue в отрыве от сервиса
- `test_security.py` — авторизация Vault (JWT / Basic)
- `test_routes.py` — интеграционные тесты API (submit, taskinfo, health)

Все внешние зависимости (Redis, Vault) мокируются.

---

## 🐳 Запуск в Docker

```bash
docker-compose up --build
```

### Файлы монтируются:
- `./config.json` → `/config.json`
- `./.secret.json` → `/.secret.json`
- `./logs/` → `/logs/`

---

## 📫 API Методы

### POST /submit
- Авторизация: JWT в `Authorization` заголовке
- Тело: JSON-TASK
- Ответ: JSON-TASK-RESPONSE или JSON-ERROR

### GET /taskinfo?taskid={UUID}
- Авторизация: JWT
- Ответ: JSON-TASK-INFO или JSON-ERROR

### POST /health
- Ответ: `{ "message": "All right", "code": 1 }` или JSON-ERROR

---

## 🛠️ Технологии

- FastAPI + Pydantic
- Redis (очереди)
- Vault (аутентификация)
- Loguru (ротация логов)
- jsonschema + pytest + coverage

---

## © COPYTRUST, 2025
