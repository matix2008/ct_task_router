"""
Настройка логирования с ротацией файлов для CT Task Router.
Логгирование основано на Loguru и управляется через config.json.
"""

import os
from datetime import timedelta
from loguru import logger
from app.config.loader import get_config


def setup_logging() -> None:
    """
    Инициализирует логирование с параметрами из конфигурационного файла.

    Ожидает следующие параметры в config["logging"]:
        - log_file: путь к файлу лога
        - level: уровень логирования (например, INFO, DEBUG)
        - rotation: объект с полями:
            - when: строка (например, "1 day", "00:00")
            - backupCount: количество дней хранения (используется как retention)
    """
    config = get_config()["logging"]

    log_file = config["log_file"]
    log_level = config["level"]
    rotation = config["rotation"]

    when = rotation.get("when", "1 day")
    backup_days = rotation.get("backupCount", 7)

    # Создание директории логов, если она не существует
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Очистка стандартных обработчиков и добавление своего
    logger.remove()
    logger.add(
        log_file,
        level=log_level,
        rotation=when,
        retention=timedelta(days=backup_days),
        enqueue=True,
        backtrace=True,
        diagnose=True
    )

    logger.info("Логирование инициализировано")
