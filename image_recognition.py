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
from calibration import SCALED_CONFIDENCE
from config import CLICK_COOLDOWN, CONFIDENCE, ACCEPT_COLOR_FALLBACK

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

# Область вікна Dota, у якій узагалі може опинитися кнопка "Прийняти",
# у частках вікна. Кнопка "Почати пошук" — теж суцільний зелений
# прямокутник з білим написом, і детектор кольору їх не розрізняє: єдина
# різниця між ними — місце. Вікно "Ваша гра готова" завжди по центру
# (макет mock_dota.render_ready_popup малює його на 0.33-0.67 ширини і
# 0.22-0.74 висоти), а кнопка пошуку гри — унизу праворуч, приблизно на
# (0.74 W, 0.82 H).
#
# Звідси межі: по горизонталі 0.20-0.80 лишає попапу запас 0.13 ширини
# вікна з кожного боку (справжній попап може бути ширшим за макет), по
# вертикалі нижня межа 0.78 стоїть рівно посередині між низом попапа
# (0.74) і верхом кнопки пошуку (0.82), а верхня 0.15 дає попапу запас
# 0.07 зверху.
ACCEPT_REGION_LEFT = 0.20
ACCEPT_REGION_TOP = 0.15
ACCEPT_REGION_RIGHT = 0.80
ACCEPT_REGION_BOTTOM = 0.78

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

def accept_region(window: Any) -> Box:
    """
    Центральна область вікна, де шукається кнопка "Прийняти".

    Args:
        window: WindowInfo вікна Dota

    Returns:
        Box в абсолютних координатах екрана
    """
    left = window.left + round(window.width * ACCEPT_REGION_LEFT)
    top = window.top + round(window.height * ACCEPT_REGION_TOP)
    right = window.left + round(window.width * ACCEPT_REGION_RIGHT)
    bottom = window.top + round(window.height * ACCEPT_REGION_BOTTOM)
    return Box(left, top, right - left, bottom - top)

def is_inside_accept_region(window: Any, box: Optional[Any]) -> bool:
    """Чи лежить знайдений прямокутник цілком у центральній області вікна."""
    if not box:
        return False

    region = accept_region(window)
    return (box.left >= region.left
            and box.top >= region.top
            and box.left + box.width <= region.left + region.width
            and box.top + box.height <= region.top + region.height)

def find_accept_by_colour(window: Any, frame: Any) -> Optional[Box]:
    """
    Знайти зелену кнопку "Прийняти" у центрі вікна.

    Пошук по всьому кадру знаходив кнопку "Почати пошук" — такий самий
    зелений прямокутник з білим написом — і натискав її, ставлячи гравця
    в чергу на матч, якого він не просив.

    Args:
        window: WindowInfo вікна Dota
        frame: знятий кадр цього вікна

    Returns:
        Box в абсолютних координатах екрана або None
    """
    region = accept_region(window)
    local_x, local_y = region.left - window.left, region.top - window.top
    crop = frame.crop((local_x, local_y,
                       local_x + region.width, local_y + region.height))

    box = find_green_button(crop, offset=(region.left, region.top))
    return box if is_inside_accept_region(window, box) else None

def locate_element(calibration: Any, name: str, window: Any, frame: Any) -> Optional[Box]:
    """
    Знайти відкалібрований елемент інтерфейсу у знятому кадрі вікна.

    Єдина реалізація для всіх, хто питає «де зараз цей елемент»: цикл бота,
    діагностичний пакет і «Перевірити зараз» у майстрі. Три копії цих
    дванадцяти рядків уже встигли розійтися — майстер шукав з іншим
    порогом, ніж бот, і рапортував «НЕ знайдено» те, що бот знаходить.

    Живе тут, а не в calibration.py: цей модуль уже володіє OpenCV, а
    сховище калібрування навмисно лишається без комп'ютерного зору.

    Args:
        calibration: сховище шаблонів (Calibration)
        name: ім'я елемента з calibration.ELEMENTS
        window: WindowInfo вікна Dota
        frame: знятий кадр цього вікна

    Returns:
        Box в абсолютних координатах екрана або None
    """
    if calibration.has(name):
        region = calibration.search_region(name, window)
        if region:
            crop = frame.crop((
                region[0] - window.left, region[1] - window.top,
                region[0] - window.left + region[2],
                region[1] - window.top + region[3],
            ))
            element = calibration.element(name)
            confidence = (
                SCALED_CONFIDENCE if element.source == "scaled"
                else CONFIDENCE.get(name, 0.8)
            )
            box = find_template(calibration.template_path(name), crop,
                                confidence=confidence, offset=region[:2])
            if box:
                return box

    # "Прийняти" знаходиться за кольором навіть без калібрування — показати
    # цей попап на вимогу неможливо, тому шаблона може ще не бути
    if name == "accept" and ACCEPT_COLOR_FALLBACK:
        return find_accept_by_colour(window, frame)

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

