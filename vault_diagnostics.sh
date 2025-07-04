#!/bin/bash

# vault_diag.sh — Диагностика Vault с логированием в файл

set -e

LOGFILE="vault_diagnostics.log"
exec > >(tee -a "$LOGFILE") 2>&1

export VAULT_ADDR="http://127.0.0.1:8200"
VAULT_CONTAINER="vault"
KEYS_DIR=".keys"
PUBLIC_KEY="$KEYS_DIR/public.pem"

step()  { echo -e "\033[1;34m[STEP]\033[0m $1"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m $1"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m $1"; }
fail()  { echo -e "\033[1;31m[FAIL]\033[0m $1"; }

echo "===== Vault Diagnostics ====="
echo "Timestamp: $(date)"
echo "Logfile: $LOGFILE"
echo

step "Проверка статуса контейнера Vault..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault status &>/dev/null; then
    ok "Контейнер Vault доступен."
else
    fail "Контейнер Vault не запущен или не отвечает!"
    exit 1
fi

step "Проверка логина через root token..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR -e VAULT_TOKEN="test-root-token" $VAULT_CONTAINER vault login test-root-token &>/dev/null; then
    ok "Root токен валиден."
else
    warn "Root токен некорректен или Vault не инициализирован."
    echo "  Рекомендации:"
    echo "   - Проверьте правильность токена и статус инициализации."
    echo "   - Если vault dev, можно задать простой root token в docker-compose."
fi

for auth in jwt userpass; do
    step "Проверка статуса auth-backend '$auth'..."
    if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault auth list | grep -q "$auth/"; then
        ok "Auth backend '$auth' включён."
    else
        warn "Auth backend '$auth' НЕ включён."
        echo "  Рекомендации:"
        echo "   - Выполните: vault auth enable $auth"
    fi
done

step "Проверка политики noop-policy..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault policy read noop-policy &>/dev/null; then
    ok "Политика noop-policy существует."
else
    warn "Политика noop-policy не найдена."
    echo "  Рекомендации:"
    echo "   - Создайте политику, например: vault policy write noop-policy <policy.hcl>"
fi

step "Проверка загрузки публичного ключа для JWT..."
if [[ -f $PUBLIC_KEY ]]; then
    ok "Публичный ключ ($PUBLIC_KEY) найден на хосте."
    # Проверим, применён ли он (поиск первого блока BEGIN PUBLIC KEY)
    PUB_START=$(head -n 1 "$PUBLIC_KEY" | tr -d '\n')
    if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault read auth/jwt/config 2>/dev/null | grep -q -- "$PUB_START"; then
        ok "Публичный ключ применён в конфиге Vault."
    else
        warn "Публичный ключ не найден в настройках JWT Vault."
        echo "  Рекомендации:"
        echo "   - Проверьте загрузку: vault write auth/jwt/config jwt_validation_pubkeys=@/tmp/public.pem bound_issuer=\"vault\""
    fi
else
    warn "Публичный ключ для JWT ($PUBLIC_KEY) не найден."
    echo "  Рекомендации:"
    echo "   - Выполните скрипт генерации ключей: jwt_keys.sh"
fi

step "Проверка пользователя userpass/service..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault list auth/userpass/users 2>/dev/null | grep -q "service"; then
    ok "Пользователь 'service' присутствует."
else
    warn "Пользователь 'service' не найден в userpass."
    echo "  Рекомендации:"
    echo "   - Добавьте пользователя: vault write auth/userpass/users/service password=\"...\" policies=\"noop-policy\""
fi

step "Проверка роли auth/jwt/role/dynamic..."
if docker exec -e VAULT_ADDR=$VAULT_ADDR $VAULT_CONTAINER vault read auth/jwt/role/dynamic &>/dev/null; then
    ok "JWT роль 'dynamic' найдена."
else
    warn "JWT роль 'dynamic' не найдена."
    echo "  Рекомендации:"
    echo "   - Создайте роль: vault write auth/jwt/role/dynamic ... (см. скрипт и документацию)"
fi

echo -e "\n\033[1;32mДиагностика завершена.\033[0m"
echo "Результаты сохранены в $LOGFILE"
