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

@dataclass
class Element:
    """Один відкалібрований елемент інтерфейсу."""
    file: str
    rect: RelRect
    source: str
    captured_at: str

class Calibration:
    """Зберігає шаблони кнопок, зняті з клієнта користувача."""

    def __init__(self, directory: Path,
                 window_size: Optional[Tuple[int, int]] = None,
                 elements: Optional[Dict[str, Element]] = None):
        self.directory = Path(directory)
        self.window_size = window_size
        self.elements: Dict[str, Element] = elements or {}

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
        file_name = f"{name}.png"
        image.save(self.directory / file_name)

        self.elements[name] = Element(
            file=file_name,
            rect=rect,
            source=source,
            captured_at=datetime.now().isoformat(timespec="seconds"),
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

    def scale_to(self, window: WindowInfo) -> None:
        """Перерахувати шаблони під новий розмір вікна."""
        if not self.window_size:
            return

        factor_x = window.width / self.window_size[0]
        factor_y = window.height / self.window_size[1]

        for name, element in self.elements.items():
            path = self.directory / element.file
            if not path.exists():
                continue

            with Image.open(path) as image:
                resized = image.resize(
                    (max(1, round(image.width * factor_x)),
                     max(1, round(image.height * factor_y))),
                    Image.LANCZOS
                )
                resized.save(path)

            element.source = "scaled"

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
