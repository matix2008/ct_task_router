#!/bin/bash
# generate_jwt_keys.sh
# Генерация RSA-ключей для подписания и проверки JWT

set -e

KEY_DIR=".keys"
PRIVATE_KEY="$KEY_DIR/private.pem"
PUBLIC_KEY="$KEY_DIR/public.pem"

mkdir -p "$KEY_DIR"

# Генерация приватного ключа
openssl genpkey -algorithm RSA -out "$PRIVATE_KEY" -pkeyopt rsa_keygen_bits:2048
chmod 600 "$PRIVATE_KEY"

# Генерация публичного ключа из приватного
openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"
chmod 644 "$PUBLIC_KEY"

echo "✅ RSA ключи сгенерированы:"
echo "   - Приватный ключ: $PRIVATE_KEY"
echo "   - Публичный ключ: $PUBLIC_KEY"
