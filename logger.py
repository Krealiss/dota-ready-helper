# -*- coding: utf-8 -*-
"""Система логування для Dota Ready Helper."""
import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(name: str = "DotaHelper", log_to_file: bool = True) -> logging.Logger:
    """Налаштувати логер з кольоровим виводом у консоль та файл."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Формат логів
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # Консольний вивід з UTF-8
    # У windowed режимі sys.stdout може бути None, тому перевіряємо
    if sys.stdout is not None:
        # Встановлюємо UTF-8 для stdout, щоб уникнути помилок з emoji
        if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Файловий вивід
    if log_to_file:
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"dota_helper_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Глобальний логер
logger = setup_logger()
