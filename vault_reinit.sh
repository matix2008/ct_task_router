#!/bin/bash

# Скрипт повторной инициализации Vault для тестовой среды (idempotent, подробные сообщения)
# Можно запускать многократно! Все критичные шаги с echo, переменные окружения используются для всех команд

set -e

export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="test-root-token"

VAULT_CONTAINER="vault"
KEYS_DIR=".keys"
PUBLIC_KEY="$KEYS_DIR/public.pem"

step() {
  echo -e "\033[1;34m[STEP]\033[0m $1"
}
ok() {
  echo -e "\033[1;32m[OK]\033[0m $1"
}
warn() {
  echo -e "\033[1;33m[WARN]\033[0m $1"
}
fail() {
  echo -e "\033[1;31m[FAIL]\033[0m $1"
}

step "Проверка статуса контейнера Vault..."
if ! docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault status &>/dev/null; then
  fail "Контейнер Vault не запущен или недоступен!"
  exit 1
fi
ok "Vault контейнер доступен."

step "Логин в Vault..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR -e VAULT_TOKEN=$VAULT_TOKEN $VAULT_CONTAINER vault login $VAULT_TOKEN &>/dev/null; then
  ok "Логин успешен."
else
  fail "Ошибка логина в Vault."
  exit 1
fi

step "Включение JWT auth backend..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault auth enable jwt &>/dev/null; then
  ok "JWT backend включён."
else
  warn "JWT backend уже был включён или возникла ошибка (игнорируется)."
fi

step "Включение Userpass auth backend..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault auth enable userpass &>/dev/null; then
  ok "Userpass backend включён."
else
  warn "Userpass backend уже был включён или возникла ошибка (игнорируется)."
fi

step "Проверка наличия публичного ключа для JWT..."
if [[ ! -f $PUBLIC_KEY ]]; then
  fail "Публичный ключ не найден ($PUBLIC_KEY). Сначала выполните jwt_keys.sh!"
  exit 1
fi
ok "Публичный ключ найден. Копируем внутрь контейнера."

docker cp $PUBLIC_KEY $VAULT_CONTAINER:/tmp/public.pem

step "Настройка JWT backend (vault write auth/jwt/config)..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault write auth/jwt/config \
  jwt_validation_pubkeys=@/tmp/public.pem \
  bound_issuer="vault" &>/dev/null; then
  ok "JWT backend сконфигурирован."
else
  warn "Возможно, config уже был настроен — проверяйте Vault UI."
fi

step "Создание политики noop-policy..." 
if echo 'path "*" { capabilities = ["read", "list"] }' | \
   docker exec -i -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault policy write noop-policy - &>/dev/null; then
  ok "Политика noop-policy установлена."
else
  warn "Ошибка при создании политики noop-policy (возможно, уже существует или возникла другая проблема)."
fi

step "Создание userpass пользователя..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault write auth/userpass/users/service \
  password="strong_password" \
  policies="noop-policy" \
  metadata="client_id=client2,role=service" &>/dev/null; then
  ok "Пользователь userpass/service создан или уже существует."
else
  warn "Ошибка создания userpass пользователя (возможно уже существует)."
fi

step "Создание роли JWT dynamic..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault write auth/jwt/role/dynamic \
  role_type="jwt" \
  bound_subject="*" \
  user_claim="sub" \
  bound_issuer="vault" \
  metadata_claims="client_id,role" \
  policies="noop-policy" \
  ttl="1h" &>/dev/null; then
  ok "JWT роль dynamic создана или обновлена."
else
  warn "Ошибка создания/обновления роли (возможно уже существует, проверьте вручную)."
fi

step "Генерация тестового JWT токена..."

PRIVATE_KEY="$KEYS_DIR/private.pem"
if [[ ! -f "$PRIVATE_KEY" ]]; then
  warn "Приватный ключ не найден ($PRIVATE_KEY). Сначала выполните jwt_keys.sh!"
  TEST_JWT=""
else
  HEADER='{"alg":"RS256","typ":"JWT"}'
  EXP=$(($(date +%s) + 600))
  PAYLOAD="{\"sub\":\"client1\",\"client_id\":\"client1\",\"role\":\"copytrust_site\",\"iss\":\"vault\",\"exp\":$EXP}"

  b64enc() { openssl base64 -e -A | tr '+/' '-_' | tr -d '='; }

  JWT_HEADER=$(echo -n "$HEADER" | b64enc)
  JWT_PAYLOAD=$(echo -n "$PAYLOAD" | b64enc)
  JWT_HEADER_PAYLOAD="$JWT_HEADER.$JWT_PAYLOAD"
  JWT_SIGNATURE=$(echo -n "$JWT_HEADER_PAYLOAD" | openssl dgst -sha256 -sign "$PRIVATE_KEY" | b64enc)
  TEST_JWT="$JWT_HEADER_PAYLOAD.$JWT_SIGNATURE"
fi

if [[ -z "$TEST_JWT" ]]; then
  warn "JWT токен не был сгенерирован (нет приватного ключа)."
else
  ok "JWT токен сгенерирован."
fi

echo "\n====================================="
echo -e "\033[1;32mГотово! Vault настроен.\033[0m"
echo "Bearer $TEST_JWT"
echo "API: http://localhost:8000"
echo "Vault UI: http://localhost:8200"
echo "====================================="
