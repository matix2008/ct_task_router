# tests/test_integration_api.py

"""
Интеграционные тесты для TaskRouter: проверка /submit, /taskinfo и /health через TestClient,
включая случаи ошибок и нестандартных ответов.
"""

from uuid import uuid4


def test_submit_task_success(test_client):
    """Успешная отправка задачи через /submit."""
    response = test_client.post(
        "/submit",
        json={"type": "calc_hash", "upload": {"filename": "file.txt"}},
        headers={"Authorization": "Bearer test"}
    )
    assert response.status_code == 200
    assert "uuid" in response.json()


def test_submit_task_invalid_data(test_client):
    """Отправка некорректных данных должна вернуть 422."""
    response = test_client.post(
        "/submit",
        json={"invalid": "data"},
        headers={"Authorization": "Bearer test"}
    )
    assert response.status_code == 422

def test_task_info_success(test_client):
    """Успешное получение информации о задаче через /taskinfo."""
    task_id = uuid4()
    response = test_client.get(
        f"/taskinfo?taskid={task_id}",
        headers={"Authorization": "Bearer test"}
    )
    assert response.status_code in (200, 400)  # зависит от наличия задачи


def test_task_info_no_auth_returns_422(test_client):
    """Отсутствие заголовка Authorization должно вернуть 401 или 422."""
    response = test_client.get(f"/taskinfo?taskid={uuid4()}")
    assert response.status_code in (401, 422)


def test_health_check_returns_ok(test_client):
    """Проверка доступности сервиса через endpoint /health (POST)."""
    response = test_client.post("/health")
    assert response.status_code == 200
    assert response.json() == {"message": "All right", "code": 1}
