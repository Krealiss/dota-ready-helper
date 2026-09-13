# -*- coding: utf-8 -*-
"""Пошук вікна Dota 2 та робота з його координатами."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pygetwindow as gw

from logger import logger

DOTA_TITLE = "Dota 2"
DOTA_PROCESS = "dota2.exe"

# Згорнуте вікно Windows повідомляє координати близько -32000
MINIMIZED_COORD = -30000

@dataclass(frozen=True)
class WindowInfo:
    """Прямокутник вікна на віртуальному робочому столі."""
    left: int
    top: int
    width: int
    height: int
    title: str

def _process_name(hwnd) -> Optional[str]:
    """Ім'я виконуваного файлу, якому належить вікно (None, якщо невідомо)."""
    if not hwnd:
        return None

    try:
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return None

        try:
            buffer = ctypes.create_unicode_buffer(260)
            size = wintypes.DWORD(len(buffer))
            if not ctypes.windll.kernel32.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(size)
            ):
                return None
            return Path(buffer.value).name.lower()
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception as e:
        logger.debug(f"Не вдалося визначити процес вікна: {e}")
        return None

def find_window() -> Optional[WindowInfo]:
    """
    Знайти вікно Dota 2.

    Заголовок звіряється точно: підрядок "Dota" ловить власне вікно
    налаштування програми.
    """
    try:
        candidates = gw.getWindowsWithTitle(DOTA_TITLE)
    except Exception as e:
        logger.debug(f"Не вдалося перелічити вікна: {e}")
        return None

    for window in candidates:
        if (window.title or "").strip() != DOTA_TITLE:
            continue

        process = _process_name(getattr(window, "_hWnd", None))
        if process is not None and process != DOTA_PROCESS:
            continue

        return WindowInfo(window.left, window.top,
                          window.width, window.height, window.title)

    return None

def is_usable(window: Optional[WindowInfo]) -> bool:
    """Чи можна знімати це вікно: не згорнуте і не вироджене."""
    if window is None:
        return False
    if window.width <= 0 or window.height <= 0:
        return False
    return window.left > MINIMIZED_COORD and window.top > MINIMIZED_COORD
