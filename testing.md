# ✅ Полный список шагов: от подготовки до начала ручного тестирования

Вот пошаговый список необходимых действий и проверок на основе загруженного файла `testing.md` — **без заголовков, без форматирования и примеров**:

1. Убедиться, что Ubuntu 22.04 установлена и подключена к интернету, IP-адрес виртуальной машины Ubuntu доступен из Windows. Если необходимо настроить сеть в VMware (NAT или Bridged) так, чтобы Windows могла обращаться к IP-адресу Ubuntu.

2. Установить в Ubuntu Docker, Docker Compose, curl, unzip и git.
   sudo apt install -y docker.io docker-compose curl unzip git

3. Добавить пользователя в группу docker и перезапустить группу
   sudo usermod -aG docker username
   newgrp docker

4. Проверить, что команды `docker` и `docker-compose` доступны.

5. Скопировать скрипт install_and_run.sh в текущую директорию.  Назначить права на запуск скрипту и запустить его
   chmod +x install_and_run.sh
   ./install_and_run.sh

6. Проверить, что запущены контейнеры `ct_task_router`, `vault`, `redis`.
   docker ps

7. Убедиться, что скрипт успешно активировал JWT и userpass, создал политику, роль и сгенерировал JWT-токен. 
   Скопировать полученный JWT-токен для дальнейших запросов.

8. Проверить доступность API по адресу
   http://192.168.119.130:8000/docs
  
9. Вызвать метод Убедиться, что сервис отвечает с кодом 200 и телом `{ "message": "All right", "code": 1 }`.
    Через PowerShell: iwr http://192.168.32.10:8000/health

10. Выполнить ручной тест POST-запроса на `/submit` Basic-авторизацией через PowerShell:

    $uri = "http://192.168.119.130:8000/submit"
    $username = "service"
    $password = "strong_password"

    $authBytes = [System.Text.Encoding]::ASCII.GetBytes("$username`:$password")
    $authEncoded = [Convert]::ToBase64String($authBytes)

    $headers = @{
        Authorization = "Basic $authEncoded"
        "Content-Type" = "application/json"
    }

    $body = @{
        ExternalId = "basic-test-001"
        type = "calc_hash"
        upload = @{ text = "some input data" }
    } | ConvertTo-Json -Depth 3

    $response = Invoke-WebRequest -Uri $uri -Method Post -Headers $headers -Body $body
    $response.Content

11. Получить UUID задачи в ответе.

12. Выполнить GET-запрос на `/taskinfo?taskid=<uuid>` с JWT-авторизацией

    $taskId = "123e4567-e89b-12d3-a456-426614174000"
    $jwt = "<ВАШ_JWT_ТОКЕН>"

    $uri = "http://192.168.32.10:8000/taskinfo?taskid=$taskId"
    $headers = @{
        Authorization = "Bearer $jwt"
    }
    $response = Invoke-WebRequest -Uri $uri -Method Get -Headers $headers
    $response.Content

13. Просмотреть логи контейнера `ct_task_router` с помощью `docker logs`.
    docker logs ct_task_router
    docker exec -it redis redis-cli
    > KEYS *

---

В случае ошибок:

1. Проверить статус Vault
   docker exec -e VAULT_ADDR=http://127.0.0.1:8200 vault vault status

2. Какие методы аутентификации включены
   docker exec -e VAULT_ADDR=http://127.0.0.1:8200 vault vault auth list

3. созданы ли политики
   docker exec -e VAULT_ADDR=http://127.0.0.1:8200 vault vault policy read noop-policy

4. есть ли пользователь service
   docker exec -e VAULT_ADDR=http://127.0.0.1:8200 vault vault read auth/userpass/users/service

5. 