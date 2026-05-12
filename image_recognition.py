# -*- coding: utf-8 -*-
"""Модуль розпізнавання зображень на екрані."""
import time
import threading
from pathlib import Path
from typing import Optional, Tuple, Any
import pyautogui as pag
from PIL import Image

from logger import logger
from config import CONFIDENCE, CLICK_COOLDOWN

# Лок для безпечних кліків з різних потоків
_gui_lock = threading.Lock()

def validate_image(path: Path) -> bool:
    """Перевірити, чи файл є валідним PNG."""
    try:
        if not path.exists():
            logger.error(f"Файл не знайдено: {path}")
            return False
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception as e:
        logger.error(f"Помилка валідації {path}: {e}")
        return False

def find_on_screen(
    image_path: Path,
    confidence: Optional[float] = None,
    region: Optional[Tuple[int, int, int, int]] = None,
    grayscale: bool = True
) -> Optional[Any]:
    """
    Знайти зображення на екрані.

    Args:
        image_path: Шлях до еталонного зображення
        confidence: Поріг впевненості (0.0-1.0)
        region: Регіон пошуку (left, top, width, height)
        grayscale: Використовувати grayscale для прискорення

    Returns:
        Box з координатами або None
    """
    try:
        conf = confidence if confidence is not None else 0.7
        return pag.locateOnScreen(
            str(image_path),
            confidence=conf,
            region=region,
            grayscale=grayscale
        )
    except pag.ImageNotFoundException:
        return None
    except Exception as e:
        logger.debug(f"Помилка пошуку {image_path.name}: {e}")
        return None

def click_center(box: Optional[Any], duration: float = 0.05) -> bool:
    """
    Клікнути по центру знайденого елемента.

    Args:
        box: Координати елемента
        duration: Тривалість руху миші

    Returns:
        True якщо клік виконано
    """
    if not box:
        return False

    x, y = pag.center(box)
    with _gui_lock:
        pag.moveTo(x, y, duration=duration)
        pag.click()

    time.sleep(CLICK_COOLDOWN)
    return True

def double_click_center(
    box: Optional[Any],
    interval: float = 0.5,
    duration: float = 0.05
) -> bool:
    """
    Подвійний клік по центру елемента.

    Args:
        box: Координати елемента
        interval: Пауза між кліками
        duration: Тривалість руху миші

    Returns:
        True якщо кліки виконано
    """
    if not box:
        return False

    x, y = pag.center(box)
    with _gui_lock:
        pag.moveTo(x, y, duration=duration)
        pag.click()
        time.sleep(interval)
        pag.click()

    time.sleep(CLICK_COOLDOWN)
    return True

def get_center_region(width: int = 800, height: int = 400) -> Tuple[int, int, int, int]:
    """
    Отримати регіон по центру екрана.

    Args:
        width: Ширина регіону
        height: Висота регіону

    Returns:
        Tuple (left, top, width, height)
    """
    sw, sh = pag.size()
    cx, cy = sw // 2, sh // 2
    return (cx - width // 2, cy - height // 2, width, height)
