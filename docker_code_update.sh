#!/bin/bash

# === Настройки ===
SERVICE=ct_task_router                    # Имя сервиса в docker-compose
COMPOSE="docker-compose"                  # Или 'docker compose' для новой версии

set -e  # Скрипт завершит работу при любой ошибке

function check {
  if [ $? -ne 0 ]; then
    echo "[FAIL] $1"
    exit 1
  fi
}

echo "[STEP] Получаем свежий код из git..."
git pull
check "Ошибка при git pull"

echo "[STEP] Останавливаем контейнер $SERVICE..."
$COMPOSE stop $SERVICE
check "Ошибка при остановке контейнера $SERVICE"

echo "[STEP] Удаляем контейнер $SERVICE..."
$COMPOSE rm -f $SERVICE
check "Ошибка при удалении контейнера $SERVICE"

echo "[STEP] Пересобираем образ $SERVICE..."
$COMPOSE build $SERVICE
check "Ошибка при пересборке образа $SERVICE"

echo "[STEP] Запускаем контейнер $SERVICE..."
$COMPOSE up -d $SERVICE
check "Ошибка при запуске контейнера $SERVICE"

echo "[OK] Контейнер $SERVICE успешно перезапущен."

echo "[STEP] Показываем логи (Ctrl+C — выйти)..."
$COMPOSE logs -f $SERVICE
