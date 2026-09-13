# -*- coding: utf-8 -*-
"""Модуль розпізнавання зображень на екрані."""
import time
import threading
from collections import namedtuple
from pathlib import Path
from typing import Optional, Tuple, Any
import pyautogui as pag
from PIL import Image

from logger import logger
from config import CONFIDENCE, CLICK_COOLDOWN

# Лок для безпечних кліків з різних потоків
_gui_lock = threading.Lock()

# Сумісний з pyautogui формат координат
Box = namedtuple("Box", "left top width height")

# Параметри пошуку зеленої кнопки за кольором (HSV, діапазон OpenCV: H 0-179).
# Покриває і темну кнопку старого вікна (H≈77), і яскраву нового (H≈58).
GREEN_HSV_LOWER = (35, 50, 45)
GREEN_HSV_UPPER = (95, 255, 255)

# Геометричні обмеження кнопки "Прийняти"
BTN_MIN_WIDTH = 150
BTN_MAX_WIDTH = 1000
BTN_MIN_HEIGHT = 28
BTN_MAX_HEIGHT = 140
BTN_MIN_ASPECT = 2.5
BTN_MAX_ASPECT = 14.0
BTN_MIN_FILL = 0.75          # суцільний прямокутник, а не рамка вікна
BTN_MIN_TEXT_RATIO = 0.01    # білий напис усередині кнопки
BTN_MAX_TEXT_RATIO = 0.45

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

def find_template(
    needle: Any,
    haystack: Any,
    confidence: Optional[float] = None,
    offset: Tuple[int, int] = (0, 0)
) -> Optional[Box]:
    """
    Знайти шаблон у готовому зображенні.

    Args:
        needle: Еталон — шлях або зображення PIL
        haystack: Де шукати — зображення PIL
        confidence: Поріг збігу (0.0-1.0)
        offset: Зсув, який додається до знайдених координат

    Returns:
        Box з координатами або None
    """
    conf = confidence if confidence is not None else 0.7

    # pyscreeze приймає лише str/ndarray/PIL.Image — Path (те, що завжди
    # повертає Calibration.template_path()) інакше валить TypeError,
    # який раніше тихо ковтався нижче і виглядав як "не знайдено".
    if isinstance(needle, Path):
        needle = str(needle)
    if isinstance(haystack, Path):
        haystack = str(haystack)

    try:
        box = pag.locate(needle, haystack, confidence=conf, grayscale=True)
    except pag.ImageNotFoundException:
        return None
    except Exception as e:
        logger.debug(f"Помилка пошуку шаблону: {e}")
        return None

    if box is None:
        return None

    return Box(box.left + offset[0], box.top + offset[1], box.width, box.height)

def find_green_button(
    image: Any,
    offset: Tuple[int, int] = (0, 0),
    debug_path: Optional[Path] = None
) -> Optional[Box]:
    """
    Знайти зелену кнопку "Прийняти" у готовому зображенні.

    Працює для будь-якого варіанту вікна "Ваша гра готова" — кнопка шукається
    як суцільний зелений прямокутник з білим написом усередині.

    Args:
        image: Зображення PIL, у якому шукати
        offset: Зсув до абсолютних координат екрана
        debug_path: Куди зберегти анотований знімок

    Returns:
        Box з абсолютними координатами або None
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.error("opencv-python не встановлено — пошук за кольором недоступний")
        return None

    try:
        return _detect_green_button(cv2, np, image, offset[0], offset[1], debug_path)
    except Exception as e:
        logger.debug(f"Помилка пошуку кнопки за кольором: {e}")
        return None

def find_green_button_on_screen(
    region: Optional[Tuple[int, int, int, int]] = None,
    debug_path: Optional[Path] = None
) -> Optional[Box]:
    """
    Сумісний врапер: сам знімає екран і шукає кнопку.

    Використовується, доки dota_helper не перейшов на знімок вікна (Task 6).
    """
    try:
        shot = pag.screenshot(region=region)
    except Exception as e:
        logger.debug(f"Не вдалось зробити скриншот: {e}")
        return None

    offset = (region[0], region[1]) if region else (0, 0)
    return find_green_button(shot, offset=offset, debug_path=debug_path)

def _detect_green_button(cv2, np, image, offset_x, offset_y, debug_path) -> Optional[Box]:
    """Внутрішня реалізація пошуку зеленої кнопки на готовому зображенні."""
    rgb = np.array(image.convert("RGB"))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat, val = hsv[..., 1], hsv[..., 2]

    mask = cv2.inRange(hsv, np.array(GREEN_HSV_LOWER), np.array(GREEN_HSV_UPPER))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    # RETR_LIST, а не RETR_EXTERNAL: кнопка лежить усередині зеленої рамки
    # вікна прийняття, тому зовнішні контури її б не повернули
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    best: Optional[Box] = None
    best_area = 0

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        if not (BTN_MIN_WIDTH <= w <= BTN_MAX_WIDTH):
            continue
        if not (BTN_MIN_HEIGHT <= h <= BTN_MAX_HEIGHT):
            continue
        if not (BTN_MIN_ASPECT <= w / h <= BTN_MAX_ASPECT):
            continue
        # Суцільна заливка, а не рамка вікна: більшість пікселів має бути зеленою
        if float(mask[y:y + h, x:x + w].mean()) / 255 < BTN_MIN_FILL:
            continue

        # Всередині кнопки має бути білий напис "ПРИНЯТИ"/"ПРИНЯТЬ"
        text_ratio = float(
            ((val[y:y + h, x:x + w] > 180) & (sat[y:y + h, x:x + w] < 60)).mean()
        )
        if not (BTN_MIN_TEXT_RATIO <= text_ratio <= BTN_MAX_TEXT_RATIO):
            continue

        if w * h > best_area:
            best_area = w * h
            best = Box(offset_x + x, offset_y + y, w, h)

    if debug_path is not None:
        annotated = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        if best:
            cv2.rectangle(
                annotated,
                (best.left - offset_x, best.top - offset_y),
                (best.left - offset_x + best.width, best.top - offset_y + best.height),
                (0, 0, 255), 2
            )
        cv2.imwrite(str(debug_path), annotated)

    return best

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
    try:
        with _gui_lock:
            pag.moveTo(x, y, duration=duration)
            pag.click()
    except pag.FailSafeException:
        # Аварійна зупинка користувачем — не глушимо
        raise
    except Exception as e:
        logger.error(f"Не вдалося клікнути ({x}, {y}): {e}")
        return False

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
    try:
        with _gui_lock:
            pag.moveTo(x, y, duration=duration)
            pag.click()
            time.sleep(interval)
            pag.click()
    except pag.FailSafeException:
        raise
    except Exception as e:
        logger.error(f"Не вдалося клікнути ({x}, {y}): {e}")
        return False

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
    # Не виходити за межі екрана, інакше скриншот регіону впаде
    width = min(width, sw)
    height = min(height, sh)
    cx, cy = sw // 2, sh // 2
    return (cx - width // 2, cy - height // 2, width, height)

if __name__ == "__main__":
    # Налагодження: показати, чи бачить бот кнопку "Прийняти" просто зараз.
    # Запуск: python image_recognition.py (вікно прийняття має бути на екрані)
    from config import (
        IMG_ACCEPT_VARIANTS, ACCEPT_REGION_WIDTH, ACCEPT_REGION_HEIGHT
    )

    test_region = get_center_region(ACCEPT_REGION_WIDTH, ACCEPT_REGION_HEIGHT)
    print(f"Регіон пошуку: {test_region}")

    for variant in IMG_ACCEPT_VARIANTS:
        found = find_on_screen(
            variant, confidence=CONFIDENCE["accept"], region=test_region
        )
        print(f"  шаблон {variant.name}: {found}")

    debug_file = Path(__file__).parent / "logs" / "accept_debug.png"
    debug_file.parent.mkdir(exist_ok=True)
    print(f"  пошук за кольором: {find_green_button_on_screen(test_region, debug_path=debug_file)}")
    print(f"Скриншот з розміткою: {debug_file}")
