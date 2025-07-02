# Dockerfile — запуск CT Task Router из корневой директории

FROM python:3.11-slim

# Отключаем буферизацию вывода
ENV PYTHONUNBUFFERED=1

# Рабочая директория — корень
WORKDIR /

# Устанавливаем зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все исходники
COPY . .

# Запуск через Uvicorn с использованием create_app() как factory
CMD ["uvicorn", "main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
