# -*- coding: utf-8 -*-
"""Калібрування: як виглядає інтерфейс Dota у конкретного користувача."""
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image

from dota_window import RelRect, WindowInfo, to_absolute
from logger import logger

FORMAT_VERSION = 1
ELEMENTS = ("search_btn", "searching", "stop", "accept")

# Область пошуку більша за кнопку в стільки разів
SEARCH_MARGIN = 2.5

# Поріг впевненості для елемента з source == "scaled": LANCZOS-масштабування
# трохи розмиває шрифт порівняно зі свіжо відрендереним текстом, тому
# перерахований шаблон вимагає нижчого порогу, ніж 0.9 для точного збігу
# пікселів на тій самій конфігурації, на якій його знято.
SCALED_CONFIDENCE = 0.65

@dataclass
class Element:
    """Один відкалібрований елемент інтерфейсу."""
    file: str
    rect: RelRect
    source: str
    captured_at: str
    # Розмір вікна на момент знімання: масштабування рахується від нього,
    # а не від поточного window_size, бо accept знімається в бою й може
    # бути знятий за іншого розміру вікна, ніж решта
    window: Optional[Tuple[int, int]] = None

class Calibration:
    """Зберігає шаблони кнопок, зняті з клієнта користувача."""

    def __init__(self, directory: Path,
                 window_size: Optional[Tuple[int, int]] = None,
                 elements: Optional[Dict[str, Element]] = None):
        self.directory = Path(directory)
        self.window_size = window_size
        self.elements: Dict[str, Element] = elements or {}

    @property
    def originals_dir(self) -> Path:
        """Незмінні знімки з клієнта — джерело для всіх масштабувань."""
        return self.directory / "originals"

    @property
    def _index_file(self) -> Path:
        return self.directory / "calibration.json"

    @classmethod
    def load(cls, directory: Path) -> "Calibration":
        """Прочитати калібрування; за будь-якої проблеми повернути порожнє."""
        directory = Path(directory)
        index = directory / "calibration.json"

        if not index.exists():
            return cls(directory)

        try:
            data = json.loads(index.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Калібрування пошкоджене, ігнорую: {e}")
            return cls(directory)

        if data.get("version") != FORMAT_VERSION:
            logger.warning(
                f"Калібрування версії {data.get('version')} несумісне — потрібне нове"
            )
            return cls(directory)

        window = data.get("window") or {}
        elements = {}
        for name, raw in (data.get("elements") or {}).items():
            rect = raw.get("rect") or {}
            elements[name] = Element(
                file=raw.get("file", f"{name}.png"),
                rect=RelRect(rect.get("x", 0.0), rect.get("y", 0.0),
                             rect.get("w", 0.0), rect.get("h", 0.0)),
                source=raw.get("source", "manual"),
                captured_at=raw.get("captured_at", ""),
                window=tuple(raw["window"]) if raw.get("window") else None,
            )

        size = (window.get("width"), window.get("height"))
        return cls(directory, size if all(size) else None, elements)

    def save(self) -> None:
        """Записати індекс калібрування."""
        self.directory.mkdir(parents=True, exist_ok=True)
        width, height = self.window_size or (0, 0)

        data = {
            "version": FORMAT_VERSION,
            "window": {"width": width, "height": height},
            "elements": {
                name: {
                    "file": element.file,
                    "rect": {"x": element.rect.x, "y": element.rect.y,
                             "w": element.rect.w, "h": element.rect.h},
                    "source": element.source,
                    "captured_at": element.captured_at,
                    "window": list(element.window) if element.window else None,
                }
                for name, element in self.elements.items()
            },
        }
        self._index_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def add(self, name: str, image: Image.Image, rect: RelRect, source: str) -> None:
        """Зберегти шаблон елемента та його місце у вікні."""
        self.directory.mkdir(parents=True, exist_ok=True)
        self.originals_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{name}.png"
        image.save(self.directory / file_name)
        # Копія, якої не торкається жодне масштабування
        image.save(self.originals_dir / file_name)

        self.elements[name] = Element(
            file=file_name,
            rect=rect,
            source=source,
            captured_at=datetime.now().isoformat(timespec="seconds"),
            window=tuple(self.window_size) if self.window_size else None,
        )
        logger.info(f"Калібрування: {name} збережено ({source})")

    def element(self, name: str) -> Optional[Element]:
        return self.elements.get(name)

    def has(self, name: str) -> bool:
        return name in self.elements and self.template_path(name).exists()

    def template_path(self, name: str) -> Path:
        element = self.elements.get(name)
        return self.directory / (element.file if element else f"{name}.png")

    def is_empty(self) -> bool:
        return not self.elements

    def is_stale(self, window: WindowInfo) -> bool:
        """Чи знято калібрування для іншого розміру вікна."""
        if not self.window_size:
            return False
        return tuple(self.window_size) != (window.width, window.height)

    def original_path(self, name: str) -> Path:
        """Незмінний знімок елемента, з якого рахуються всі масштабування."""
        element = self.elements.get(name)
        return self.originals_dir / (element.file if element else f"{name}.png")

    def scale_to(self, window: WindowInfo) -> None:
        """
        Перерахувати шаблони під новий розмір вікна.

        Рахуємо завжди від оригіналу, знятого з клієнта, а не від попереднього
        результату. Інакше кожна зміна розміру накладає ще одну передискретизацію
        на вже розмиту картинку: на живій машині вікно, яке перетягують на інший
        монітор, дало ланцюг 1920x1080 -> 3200x1800 -> 2400x1350 -> 3200x1800 і
        за півхвилини знищило робоче калібрування.
        """
        if not self.window_size:
            return

        for name, element in self.elements.items():
            source_path = self.original_path(name)
            if not source_path.exists():
                # Калібрування, зняте до появи originals/: іншого джерела немає
                source_path = self.directory / element.file
            if not source_path.exists():
                continue

            # Інтерфейс Dota масштабується за висотою вікна і зберігає пропорції
            # елементів — окремі коефіцієнти для ширини й висоти спотворювали б
            # шаблон на будь-якому співвідношенні сторін, відмінному від того,
            # на якому знято калібрування (напр. 21:9 проти 16:9).
            captured_height = (element.window or self.window_size)[1]
            factor = window.height / captured_height

            with Image.open(source_path) as image:
                resized = image.resize(
                    (max(1, round(image.width * factor)),
                     max(1, round(image.height * factor))),
                    Image.LANCZOS
                )
                resized.save(self.directory / element.file)

            element.source = element.source if factor == 1 else "scaled"

        self.window_size = (window.width, window.height)
        self.save()
        logger.info(
            f"Калібрування перераховано під {window.width}x{window.height}"
        )

    def search_region(self, name: str, window: WindowInfo) -> Optional[tuple]:
        """Область пошуку навколо запам'ятованого місця елемента."""
        element = self.elements.get(name)
        if element is None:
            return None

        x, y, width, height = to_absolute(window, element.rect)
        center_x, center_y = x + width / 2, y + height / 2
        half_w, half_h = width * SEARCH_MARGIN / 2, height * SEARCH_MARGIN / 2

        left = max(window.left, int(center_x - half_w))
        top = max(window.top, int(center_y - half_h))
        right = min(window.left + window.width, int(center_x + half_w))
        bottom = min(window.top + window.height, int(center_y + half_h))

        return (left, top, right - left, bottom - top)
