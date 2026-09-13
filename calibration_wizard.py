# -*- coding: utf-8 -*-
"""Майстер калібрування: зняти мірки кнопок з клієнта користувача."""
from pathlib import Path
from typing import List, Optional

import numpy as np
from PIL import Image

from config import ASSETS_DIR
from image_recognition import Box, find_green_button, find_template
from logger import logger

# Діапазон масштабів автопошуку зі специфікації
SCALES = [round(0.5 + 0.1 * i, 1) for i in range(16)]

# Кадр темніший за це значення вважається порожнім
BLANK_THRESHOLD = 8

# Кандидати, що перетинаються більше ніж наполовину, вважаються одним елементом
OVERLAP_LIMIT = 0.5

SHIPPED = {
    "search_btn": ["search_game.png"],
    "searching": ["is_searching_game.png"],
    "stop": ["stop.png"],
    "accept": ["prinyat.png"],
}

def shipped_templates(name: str) -> List[Path]:
    """Наші готові шаблони для елемента — лише як підказка в майстрі."""
    return [ASSETS_DIR / file for file in SHIPPED.get(name, [])
            if (ASSETS_DIR / file).exists()]

def is_blank(frame: Image.Image) -> bool:
    """Чи знімок майже повністю чорний (ексклюзивний повноекранний режим)."""
    return float(np.array(frame.convert("L")).mean()) < BLANK_THRESHOLD

def _overlaps(first: Box, second: Box) -> bool:
    """Чи два прямокутники описують той самий елемент."""
    dx = min(first.left + first.width, second.left + second.width) - max(first.left, second.left)
    dy = min(first.top + first.height, second.top + second.height) - max(first.top, second.top)
    if dx <= 0 or dy <= 0:
        return False

    smaller = min(first.width * first.height, second.width * second.height)
    return (dx * dy) / smaller > OVERLAP_LIMIT

def _match_score(needle, haystack):
    """Кореляція шаблону з кадром: (оцінка, (x, y) лівого верхнього кута)."""
    import cv2

    needle_gray = cv2.cvtColor(np.array(needle.convert("RGB")), cv2.COLOR_RGB2GRAY)
    haystack_gray = cv2.cvtColor(np.array(haystack.convert("RGB")), cv2.COLOR_RGB2GRAY)
    result = cv2.matchTemplate(haystack_gray, needle_gray, cv2.TM_CCOEFF_NORMED)
    _, score, _, location = cv2.minMaxLoc(result)
    return float(score), location

def detect_candidates(frame: Image.Image, templates: List[Path],
                      confidence: Optional[float] = None) -> List[Box]:
    """
    Знайти на кадрі місця, схожі на кнопку.

    Шаблони перебираються в діапазоні масштабів, бо розмір інтерфейсу
    користувача заздалегідь невідомий. Кандидати ранжуються за кореляцією
    та дедублюються по перекриттю.
    """
    conf = confidence if confidence is not None else 0.7
    candidates: List[tuple[float, Box]] = []

    for template in templates:
        try:
            with Image.open(template) as original:
                needle = original.convert("RGB")
        except Exception as e:
            logger.debug(f"Не вдалося прочитати шаблон {template}: {e}")
            continue

        for scale in SCALES:
            size = (max(1, round(needle.width * scale)),
                    max(1, round(needle.height * scale)))
            if size[0] > frame.width or size[1] > frame.height:
                continue

            resized = needle.resize(size, Image.LANCZOS)
            try:
                score, (x, y) = _match_score(resized, frame)
            except Exception as e:
                logger.debug(f"Помилка обчислення кореляції для шаблону {template} на масштабі {scale}: {e}")
                continue

            if score >= conf:
                candidates.append((score, Box(x, y, size[0], size[1])))

    # Сортувати за оцінкою у спаданні та дедублювати перекриваючі кандидати
    candidates.sort(key=lambda x: x[0], reverse=True)
    found: List[Box] = []
    for score, box in candidates:
        if not any(_overlaps(box, existing) for existing in found):
            found.append(box)

    return found

def detect_accept(frame: Image.Image) -> Optional[Box]:
    """Кнопку 'Прийняти' шукаємо за кольором — вона не залежить від мови."""
    return find_green_button(frame)
