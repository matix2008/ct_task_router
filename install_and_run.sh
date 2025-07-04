#!/bin/bash

# Завершаем скрипт при любой ошибке
set -e

# Переменные окружения Vault
VAULT_CONTAINER="vault"
VAULT_TOKEN="test-root-token"
VAULT_ADDR="http://127.0.0.1:8200"

echo "🔧 Проверка наличия Docker и Docker Compose..."

# Проверка наличия Docker
if ! command -v docker &>/dev/null; then
    echo "❌ Docker не установлен. Установите его вручную."
    exit 1
fi

# Проверка наличия Docker Compose
if ! command -v docker-compose &>/dev/null; then
    echo "❌ Docker Compose не установлен. Установите его вручную."
    exit 1
fi

echo "✅ Docker и Docker Compose найдены."

# --- Создание рабочей директории ---
WORKDIR="$HOME/work/ct_task_router_test"
mkdir -p "$WORKDIR"
cd "$WORKDIR"
echo "📁 Рабочая директория: $WORKDIR"

# --- Выгрузка файлов из репозитория ---
git clone https://github.com/matix2008/ct_task_router .
echo "Репозиторий склонирован в $WORKDIR"

# --- Создание каталога для логов с нужными правами ---
mkdir -p logs
chmod 755 logs                       # разрешить чтение и запись от пользователя
chown $(id -u):$(id -g) logs         # владельцем становится текущий пользователь
echo "📂 Каталог logs/ создан и доступен для записи"

# --- Создание файла config.json с настройками сервиса ---
cat > config.json <<EOF
{
  "vault": {
    "url": "http://vault:8200",
    "auth_path": "auth/jwt"
  },
  "queue": {
    "type": "redis",
    "url": "redis://redis:6379"
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
EOF

chmod 644 config.json  # доступен только для чтения (в контейнере монтируется с :ro)
echo "📝 config.json создан"

# --- Создание файла .secrets.json с токеном и кредами Redis ---
cat > .secrets.json <<EOF
{
  "redis": {
    "username": "",
    "password": ""
  },
  "vault": {
    "token": "test-root-token"
  }
}
EOF

chmod 600 .secrets.json  # защита от чтения другими пользователями
echo "🔐 .secrets.json создан и защищён"

# --- Проверка наличия docker-compose.yml ---
if [[ ! -f docker-compose.yml ]]; then
    echo "❌ Файл docker-compose.yml не найден. Скопируйте его в $WORKDIR"
    exit 1
fi

# --- Проверка наличия Dockerfile ---
if [[ ! -f Dockerfile ]]; then
    echo "❌ Файл Dockerfile не найден. Скопируйте его в $WORKDIR"
    exit 1
fi

# --- Сборка и запуск контейнеров в фоне ---
echo "🐳 Сборка и запуск сервисов..."
docker-compose up --build -d

# --- Небольшая пауза, чтобы Vault успел стартовать ---
echo "⏳ Ожидание запуска Vault..."
sleep 10  # даём время на инициализацию Vault

# --- Генерация и настройка Vault ---
echo "Для настройки Vault запустите последовательно скрипты jwt_keys.sh и vault_reinit.sh"
