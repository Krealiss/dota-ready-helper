# -*- coding: utf-8 -*-
"""Діагностичний пакет для розбору поламок у користувачів."""
import ctypes
import json
import platform
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from PIL import Image

from config import APP_VERSION
from image_recognition import locate_element
from logger import logger

def _screens() -> dict:
    """Розміри основного екрана та всього віртуального робочого столу."""
    try:
        user32 = ctypes.windll.user32
        return {
            "primary": [user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)],
            "virtual": [user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)],
            "virtual_offset": [user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)],
        }
    except Exception as e:
        logger.debug(f"Не вдалося опитати екрани: {e}")
        return {}

def detect_elements(window, frame, calibration) -> Dict[str, Optional[bool]]:
    """
    Перевірити, чи знаходяться відкалібровані елементи у поточному кадрі.

    Повертає dict[ім'я → None (невідомо) | False (не знайдено) | True (знайдено)].
    None означає, що не можна перевірити (немає вікна чи кадру).
    """
    result = {}

    for name in calibration.elements.keys():
        # Якщо немає вікна чи кадру, результат невідомий для кожного елемента
        if window is None or frame is None:
            result[name] = None
            continue

        result[name] = locate_element(calibration, name, window, frame) is not None

    return result

def collect_report(window, calibration, frame=None) -> dict:
    """Зібрати опис середовища. Жодних даних з .env."""
    return {
        "app_version": APP_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "screens": _screens(),
        "window": None if window is None else {
            "left": window.left, "top": window.top,
            "width": window.width, "height": window.height,
        },
        "calibration": {
            "window": list(calibration.window_size) if calibration.window_size else None,
            "elements": {
                name: {"source": element.source,
                       "captured_at": element.captured_at,
                       "rect": [element.rect.x, element.rect.y,
                                element.rect.w, element.rect.h]}
                for name, element in calibration.elements.items()
            },
        },
        "detection": detect_elements(window, frame, calibration),
    }

def build_bundle(out_dir: Path, window, calibration,
                 frame: Optional[Image.Image] = None) -> Path:
    """
    Скласти архів зі звітом і знімком вікна.

    У архів потрапляє знімок гри — на ньому видно нік у Steam. Вміст .env
    не додається за жодних умов.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle = out_dir / f"diagnostics_{stamp}.zip"
    report = collect_report(window, calibration, frame)

    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("report.json",
                         json.dumps(report, indent=2, ensure_ascii=False))

        if frame is not None:
            screenshot = out_dir / "screenshot.png"
            frame.save(screenshot)
            archive.write(screenshot, "screenshot.png")
            screenshot.unlink()

        for name, element in calibration.elements.items():
            path = calibration.directory / element.file
            if path.exists():
                archive.write(path, f"calibration/{element.file}")

    logger.info(f"Діагностичний архів: {bundle}")
    return bundle
