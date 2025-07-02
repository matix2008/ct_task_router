# tests/test_security.py

"""
Unit-тесты для класса VaultClient.
Проверяется аутентификация JWT и Basic, а также проверка прав и ошибок.
"""

from unittest.mock import MagicMock, patch
import base64
import pytest
from fastapi import HTTPException
from app.auth.security import VaultClient


@pytest.fixture(name="fake_hvac_client")
def fake_hvac_client_fixtures():
    """
    Мок-объект hvac.Client.
    """
    return MagicMock()


@pytest.fixture(name="vault_client")
def vault_client_fixtures(fake_hvac_client):
    """
    VaultClient с мокнутым hvac.Client.
    """
    return VaultClient(
        client=fake_hvac_client,
        vault_url="http://vault:8200",
        auth_path="auth/jwt"
    )


def test_authenticate_jwt_success(vault_client):
    """
    Успешная аутентификация JWT-токеном.
    """
    token = "Bearer mock.jwt.token"
    vault_client.verify_jwt = MagicMock(return_value=("user", "admin"))
    user, role = vault_client.authenticate_user(token, "calc_hash")
    assert user == "user"
    assert role == "admin"


def test_authenticate_basic_success(vault_client):
    """
    Успешная Basic-аутентификация.
    """
    credentials = base64.b64encode(b"user:pass").decode()
    header = f"Basic {credentials}"
    vault_client.verify_basic = MagicMock(return_value=("user", "service"))

    user, role = vault_client.authenticate_user(header, "calc_hash")
    assert user == "user"
    assert role == "service"


def test_is_authorized():
    """
    Проверка прав доступа для разных ролей и действий.
    """
    v = VaultClient(client=MagicMock(), vault_url="x", auth_path="y")

    assert v.is_authorized("admin", "anything") is True
    assert v.is_authorized("service", "calc_hash") is True
    assert v.is_authorized("service", "resize_image") is False
    assert v.is_authorized("copytrust_site", "calc_hash") is True
    assert v.is_authorized("copytrust_site", "other") is False


def test_authenticate_user_invalid_header(vault_client):
    """
    Ошибка при отсутствии корректного заголовка.
    """
    with pytest.raises(HTTPException) as exc:
        vault_client.authenticate_user("Token something", "calc_hash")
    assert exc.value.status_code == 401


def test_verify_jwt_success(vault_client):
    """Успешная валидация JWT токена через Vault"""
    vault_client.client.auth.jwt_login.return_value = {
        "metadata": {"client_id": "user1", "role": "admin"}
    }
    client_id, role = vault_client.verify_jwt("token.jwt", "calc_hash")
    assert client_id == "user1"
    assert role == "admin"


def test_verify_jwt_missing_metadata(vault_client):
    """Ошибка: в metadata отсутствует client_id или role"""
    vault_client.client.auth.jwt_login.return_value = {"metadata": {}}
    with pytest.raises(HTTPException) as exc:
        vault_client.verify_jwt("token.jwt", "calc_hash")
    assert exc.value.status_code == 400


def test_verify_jwt_forbidden_action(vault_client):
    """Ошибка: роль не имеет доступа к действию"""
    vault_client.client.auth.jwt_login.return_value = {
        "metadata": {"client_id": "u1", "role": "copytrust_site"}
    }
    with pytest.raises(HTTPException) as exc:
        vault_client.verify_jwt("token.jwt", "resize_image")
    assert exc.value.status_code == 403


def test_verify_basic_success(vault_client):
    """Успешная Basic-аутентификация через userpass Vault"""
    vault_client.client.userpass_login.return_value = {
        "metadata": {"client_id": "svc1", "role": "service"}
    }
    client_id, role = vault_client.verify_basic("svc1", "secret", "water_marks")
    assert client_id == "svc1"
    assert role == "service"


def test_authenticate_user_exception_handling():
    """Ошибка: verify_jwt выбрасывает исключение → возвращается HTTP 401"""
    with patch("app.auth.security.VaultClient.verify_jwt", side_effect=Exception("Vault error")):
        vault = VaultClient(client=MagicMock(), vault_url="url", auth_path="jwt")
        with pytest.raises(HTTPException) as exc:
            vault.authenticate_user("Bearer broken.jwt", "calc_hash")
        assert exc.value.status_code == 401
        assert "Authentication failed" in str(exc.value.detail)
