# Universal UI Recognition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Зробити так, щоб Dota Ready Helper працював у гравця з будь-якою роздільною здатністю, мовою клієнта, масштабом інтерфейсу та розташуванням вікна.

**Architecture:** Усі координати рахуються від вікна Dota 2, а не від екрана. Шаблони кнопок знімаються з клієнта самого користувача майстром калібрування, тому мова й масштаб зашиті в дані, а не вгадуються. Кнопка «Прийняти» шукається за кольором і самокалібрується під час першого спійманого матчу, бо її попап неможливо викликати на замовлення.

**Tech Stack:** Python 3.12+, pygetwindow + ctypes (вікно), Pillow ImageGrab (знімок), OpenCV + pyscreeze (розпізнавання), PyQt6 (майстер), keyboard (гаряча клавіша), pytest.

**Spec:** `docs/superpowers/specs/2026-09-14-universal-recognition-design.md`

## Global Constraints

- **Жодних нових залежностей.** Усе потрібне вже є в `requirements.txt`: `pygetwindow` і `pyscreeze` приходять з `pyautogui`, решта — `Pillow`, `opencv-python`, `PyQt6`, `keyboard`, `requests`, `pyTelegramBotAPI`, `python-dotenv`. `ctypes` і `zipfile` — зі стандартної бібліотеки.
- **Windows-only виклики через `ctypes` обгортаються try/except** і мають працювати у вигляді «не вдалося перевірити — пишемо в лог і йдемо далі».
- **Мова коду:** докстринги й коментарі українською, як у всьому проєкті. Імена функцій і змінних — англійською.
- **Повідомлення комітів:** англійською, наказовий спосіб, як у наявній історії (`Add first-run setup wizard for Telegram credentials`). Не conventional commits. Кожен коміт закінчується рядком `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Наявні 86 тестів мають лишатися зеленими** після кожного коміту. Перевірка: `python -m pytest tests -q`.
- **CI:** `.github/workflows/tests.yml`, `windows-latest`, Python 3.12. Усі нові тести мають працювати headless — без справжньої Dota, без справжнього екрана, без показаних вікон Qt.
- **Формат калібрування:** `version: 1`. Файл іншої версії відкидається з повідомленням, програма не падає.
- **Константи зі спеки, копіювати дослівно:** `SEARCH_MARGIN = 2.5`, `NO_GAME_POLL_INTERVAL = 2.0`, діапазон масштабів автопошуку `0.5–2.0`, назва вікна `"Dota 2"`, процес `"dota2.exe"`, елементи `("search_btn", "searching", "stop", "accept")`.
- **Приватність:** вміст `.env` і токен бота не потрапляють у діагностичний архів за жодних умов.

---

### Task 1: Пошук вікна Dota

**Files:**
- Create: `dota_window.py`
- Test: `tests/test_dota_window.py`

**Interfaces:**
- Consumes: нічого
- Produces: `WindowInfo(left: int, top: int, width: int, height: int, title: str)`, `find_window() -> Optional[WindowInfo]`, `is_usable(window: WindowInfo) -> bool`, константи `DOTA_TITLE = "Dota 2"`, `DOTA_PROCESS = "dota2.exe"`

Пошук за підрядком «Dota» знаходить власне вікно програми («Dota Ready Helper — налаштування»), тому збіг заголовка має бути точним, а ім'я процесу — перевіреним.

- [ ] **Step 1: Написати тест, що падає**

```python
# tests/test_dota_window.py
from types import SimpleNamespace

import pytest

import dota_window as dw


def fake_window(title, left=0, top=0, width=1920, height=1080, hwnd=1):
    return SimpleNamespace(title=title, left=left, top=top,
                           width=width, height=height, _hWnd=hwnd)


@pytest.fixture
def windows(monkeypatch):
    """Підмінити перелік вікон і перевірку процесу."""
    state = {"windows": [], "process": "dota2.exe"}
    monkeypatch.setattr(dw.gw, "getWindowsWithTitle",
                        lambda title: list(state["windows"]))
    monkeypatch.setattr(dw, "_process_name", lambda hwnd: state["process"])
    return state


def test_finds_dota_window(windows):
    windows["windows"] = [fake_window("Dota 2", left=-254, top=-1440)]

    found = dw.find_window()

    assert found is not None
    assert (found.left, found.top, found.width, found.height) == (-254, -1440, 1920, 1080)


def test_ignores_our_own_setup_window(windows):
    """Регресія: пошук за підрядком знаходив вікно налаштування програми."""
    windows["windows"] = [fake_window("Dota Ready Helper — налаштування")]

    assert dw.find_window() is None


def test_ignores_window_from_another_process(windows):
    windows["windows"] = [fake_window("Dota 2")]
    windows["process"] = "chrome.exe"

    assert dw.find_window() is None


def test_accepts_window_when_process_check_unavailable(windows):
    """Якщо ctypes не спрацював, довіряємо заголовку."""
    windows["windows"] = [fake_window("Dota 2")]
    windows["process"] = None

    assert dw.find_window() is not None


@pytest.mark.parametrize("left,top,width,height,expected", [
    (0, 0, 1920, 1080, True),
    (-254, -1440, 1920, 1080, True),      # другий монітор
    (-32000, -32000, 1920, 1080, False),  # згорнуте вікно
    (0, 0, 0, 0, False),
    (0, 0, 1920, 0, False),
])
def test_is_usable(left, top, width, height, expected):
    window = dw.WindowInfo(left, top, width, height, "Dota 2")

    assert dw.is_usable(window) is expected
```

- [ ] **Step 2: Запустити тест і переконатися, що він падає**

Run: `python -m pytest tests/test_dota_window.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dota_window'`

- [ ] **Step 3: Написати мінімальну реалізацію**

```python
# dota_window.py
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
```

- [ ] **Step 4: Запустити тести**

Run: `python -m pytest tests/test_dota_window.py -v && python -m pytest tests -q`
Expected: нові тести PASS, наявні 86 лишаються зеленими

- [ ] **Step 5: Закомітити**

```bash
git add dota_window.py tests/test_dota_window.py
git commit -m "$(cat <<'EOF'
Add Dota 2 window discovery

Searching windows by the substring "Dota" matches the helper's own setup
window, so the title must match exactly and the owning process is verified
through ctypes. Falls back to the title alone when the process cannot be
queried.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Геометрія вікна та знімок

**Files:**
- Modify: `dota_window.py`
- Test: `tests/test_dota_window.py`

**Interfaces:**
- Consumes: `WindowInfo` з Task 1
- Produces: `RelRect(x: float, y: float, w: float, h: float)`, `to_absolute(window, rel) -> tuple[int, int, int, int]`, `to_relative(window, abs_rect) -> RelRect`, `capture(window) -> PIL.Image.Image`

`pyautogui.screenshot` не вміє від'ємних координат другого монітора, тому знімок робиться через `ImageGrab.grab(bbox, all_screens=True)`.

- [ ] **Step 1: Написати тест, що падає**

```python
# додати в tests/test_dota_window.py
from PIL import Image


def test_relative_to_absolute_round_trip():
    window = dw.WindowInfo(-254, -1440, 1920, 1080, "Dota 2")
    rect = (window.left + 480, window.top + 540, 384, 108)

    rel = dw.to_relative(window, rect)
    back = dw.to_absolute(window, rel)

    assert rel.x == pytest.approx(0.25) and rel.y == pytest.approx(0.5)
    assert rel.w == pytest.approx(0.2) and rel.h == pytest.approx(0.1)
    assert back == rect


def test_relative_rect_survives_resolution_change():
    """Частки переносять місце кнопки на інше вікно."""
    small = dw.WindowInfo(0, 0, 1920, 1080, "Dota 2")
    large = dw.WindowInfo(0, 0, 2560, 1440, "Dota 2")

    rel = dw.to_relative(small, (1420, 890, 330, 50))

    assert dw.to_absolute(large, rel) == (1893, 1187, 440, 67)


def test_capture_grabs_window_across_all_screens(monkeypatch):
    """Другий монітор дає від'ємні координати — потрібен all_screens."""
    calls = {}

    def fake_grab(bbox=None, all_screens=False, **kwargs):
        calls["bbox"] = bbox
        calls["all_screens"] = all_screens
        return Image.new("RGB", (1920, 1080), (10, 10, 10))

    monkeypatch.setattr(dw.ImageGrab, "grab", fake_grab)
    window = dw.WindowInfo(-254, -1440, 1920, 1080, "Dota 2")

    frame = dw.capture(window)

    assert calls["bbox"] == (-254, -1440, 1666, -360)
    assert calls["all_screens"] is True
    assert frame.size == (1920, 1080)
```

- [ ] **Step 2: Запустити тест і переконатися, що він падає**

Run: `python -m pytest tests/test_dota_window.py -k "relative or capture" -v`
Expected: FAIL — `AttributeError: module 'dota_window' has no attribute 'to_relative'`

- [ ] **Step 3: Написати мінімальну реалізацію**

```python
# додати в dota_window.py
from PIL import Image, ImageGrab

@dataclass(frozen=True)
class RelRect:
    """Прямокутник у частках клієнтської області вікна."""
    x: float
    y: float
    w: float
    h: float

def to_absolute(window: WindowInfo, rel: RelRect) -> tuple:
    """Перевести частки вікна в екранні координати."""
    return (
        window.left + round(rel.x * window.width),
        window.top + round(rel.y * window.height),
        round(rel.w * window.width),
        round(rel.h * window.height),
    )

def to_relative(window: WindowInfo, rect: tuple) -> RelRect:
    """Перевести екранні координати в частки вікна."""
    left, top, width, height = rect
    return RelRect(
        (left - window.left) / window.width,
        (top - window.top) / window.height,
        width / window.width,
        height / window.height,
    )

def capture(window: WindowInfo) -> Image.Image:
    """
    Зняти вікно Dota.

    ImageGrab з all_screens=True, бо pyautogui.screenshot не бачить
    моніторів з від'ємними координатами.
    """
    bbox = (window.left, window.top,
            window.left + window.width, window.top + window.height)
    return ImageGrab.grab(bbox=bbox, all_screens=True).convert("RGB")
```

- [ ] **Step 4: Запустити тести**

Run: `python -m pytest tests/test_dota_window.py -v && python -m pytest tests -q`
Expected: усі PASS

- [ ] **Step 5: Закомітити**

```bash
git add dota_window.py tests/test_dota_window.py
git commit -m "$(cat <<'EOF'
Add window-relative geometry and multi-monitor capture

Coordinates are stored as fractions of the window so a remembered button
position carries over to any resolution. Capture goes through ImageGrab with
all_screens because pyautogui cannot reach monitors at negative coordinates.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Розпізнавання як чисті операції над зображеннями

**Files:**
- Modify: `image_recognition.py:81` (`find_green_button`), `image_recognition.py:119` (`_detect_green_button`)
- Modify: `tests/test_accept_detection.py:113-156`
- Test: `tests/test_accept_detection.py`

**Interfaces:**
- Consumes: нічого
- Produces: `find_template(needle, haystack, confidence=None, offset=(0, 0)) -> Optional[Box]`, `find_green_button(image, offset=(0, 0), debug_path=None) -> Optional[Box]`, `find_green_button_on_screen(region, debug_path=None) -> Optional[Box]` (тимчасовий сумісний врапер для `dota_helper`, прибирається в Task 6)

Зараз `find_green_button` сама робить знімок екрана, тому тести змушені підміняти `pag.screenshot`. Після зміни функція приймає готове зображення: і чесніше, і тестувати простіше, і потрібне для «одного знімка за ітерацію».

- [ ] **Step 1: Переписати наявні тести під нову сигнатуру**

```python
# tests/test_accept_detection.py — замінити фікстуру screen і виклики
@pytest.fixture
def screen():
    """Повертає обрізаний під регіон кадр — так, як його віддасть dota_window."""

    def _crop(img):
        x, y, w, h = REGION
        return img.crop((x, y, x + w, y + h))

    return _crop


@pytest.mark.parametrize("builder", [new_dialog, gradient_dialog, old_dialog],
                         ids=["all_pick", "gradient", "old"])
def test_green_button_found(screen, builder):
    img, expected = builder()

    box = ir.find_green_button(screen(img), offset=REGION[:2])

    assert box is not None, "кнопку 'Прийняти' не знайдено"
    x, y, w, h = expected
    assert abs(box.left - x) <= 4 and abs(box.top - y) <= 4
    assert abs(box.width - w) <= 8 and abs(box.height - h) <= 8


def test_find_template_locates_crop_in_frame():
    """Новий пошук за шаблоном працює над зображеннями, не над екраном."""
    frame, expected = new_dialog()
    x, y, w, h = expected
    needle = frame.crop((x, y, x + w, y + h))

    box = ir.find_template(needle, frame, confidence=0.9)

    assert box is not None
    assert abs(box.left - x) <= 2 and abs(box.top - y) <= 2


def test_find_template_returns_none_when_absent():
    frame, _ = game_screen()
    needle, expected = new_dialog()
    x, y, w, h = expected

    assert ir.find_template(needle.crop((x, y, x + w, y + h)), frame,
                            confidence=0.9) is None
```

Решту тестів у файлі (`test_click_lands_on_button`, `test_no_false_positive_on_game_screen`, `test_button_inside_green_frame_is_not_skipped`) привести до того самого виклику `ir.find_green_button(screen(img), offset=REGION[:2])`. Тест `test_center_region_is_clamped_to_screen` лишити без змін — `get_center_region` прибирається в Task 6.

- [ ] **Step 2: Запустити тести і переконатися, що вони падають**

Run: `python -m pytest tests/test_accept_detection.py -v`
Expected: FAIL — `find_green_button() got an unexpected keyword argument 'offset'`

- [ ] **Step 3: Переписати функції**

```python
# image_recognition.py — замінити find_green_button і _detect_green_button
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
```

У `_detect_green_button` замінити перший рядок `rgb = np.array(shot.convert("RGB"))` на `rgb = np.array(image.convert("RGB"))` і перейменувати параметр `shot` на `image`.

- [ ] **Step 4: Оновити виклик у dota_helper і запустити всі тести**

У `dota_helper.py:133` замінити `find_green_button(self.accept_region)` на `find_green_button_on_screen(self.accept_region)`, а в імпорті на рядку 14 — `find_green_button` на `find_green_button_on_screen`. У блоці `if __name__ == "__main__"` у `image_recognition.py` замінити виклик `find_green_button(test_region, debug_path=debug_file)` на `find_green_button_on_screen(test_region, debug_path=debug_file)`.

Run: `python -m pytest tests -q`
Expected: 86 наявних + 2 нових PASS

- [ ] **Step 5: Закомітити**

```bash
git add image_recognition.py dota_helper.py tests/test_accept_detection.py
git commit -m "$(cat <<'EOF'
Make recognition work on images instead of the screen

find_green_button grabbed its own screenshot, which forced every test to
patch pyautogui and made it impossible to reuse one frame for several
checks. It now takes a PIL image plus an offset, and find_template does the
same for template matching. A thin on-screen wrapper keeps dota_helper
working until it is rewired to window captures.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Сховище калібрування

**Files:**
- Create: `calibration.py`
- Test: `tests/test_calibration.py`

**Interfaces:**
- Consumes: `WindowInfo`, `RelRect`, `to_absolute`, `to_relative` з `dota_window`
- Produces: `ELEMENTS`, `SEARCH_MARGIN`, `FORMAT_VERSION`, `Element(file, rect, source, captured_at)`, `Calibration` з методами `load(directory)`, `save()`, `add(name, image, rect, source)`, `element(name)`, `template_path(name)`, `has(name)`, `is_empty()`, `is_stale(window)`, `scale_to(window)`, `search_region(name, window)`

- [ ] **Step 1: Написати тест, що падає**

```python
# tests/test_calibration.py
import json

import pytest
from PIL import Image

import calibration as cal
from dota_window import RelRect, WindowInfo

WINDOW = WindowInfo(0, 0, 1920, 1080, "Dota 2")
BIG_WINDOW = WindowInfo(-254, -1440, 2560, 1440, "Dota 2")


@pytest.fixture
def store(tmp_path):
    return cal.Calibration.load(tmp_path / "calibration")


def button(width=330, height=50):
    return Image.new("RGB", (width, height), (62, 123, 54))


def test_empty_store_has_no_elements(store):
    assert store.is_empty() is True
    assert store.element("search_btn") is None
    assert store.has("search_btn") is False


def test_add_and_reload_round_trip(store, tmp_path):
    store.window_size = (1920, 1080)
    store.add("search_btn", button(), RelRect(0.741, 0.823, 0.171, 0.045), "manual")
    store.save()

    reloaded = cal.Calibration.load(tmp_path / "calibration")
    element = reloaded.element("search_btn")

    assert element.source == "manual"
    assert element.rect.x == pytest.approx(0.741)
    assert reloaded.template_path("search_btn").exists()
    assert reloaded.window_size == (1920, 1080)


def test_search_region_expands_around_remembered_place(store):
    store.window_size = (1920, 1080)
    store.add("search_btn", button(), RelRect(0.5, 0.5, 0.1, 0.05), "auto")

    left, top, width, height = store.search_region("search_btn", WINDOW)

    # 0.1*1920 = 192 -> 192*2.5 = 480; 0.05*1080 = 54 -> 54*2.5 = 135
    assert (width, height) == (480, 135)
    assert left == 960 + 96 - 240        # центр кнопки мінус половина області
    assert top == 540 + 27 - 67


def test_search_region_is_clamped_to_window(store):
    store.window_size = (1920, 1080)
    store.add("stop", button(), RelRect(0.0, 0.0, 0.1, 0.05), "auto")

    left, top, width, height = store.search_region("stop", WINDOW)

    assert left >= WINDOW.left and top >= WINDOW.top
    assert left + width <= WINDOW.left + WINDOW.width


def test_search_region_none_for_unknown_element(store):
    assert store.search_region("accept", WINDOW) is None


def test_is_stale_when_window_size_changed(store):
    store.window_size = (1920, 1080)

    assert store.is_stale(WINDOW) is False
    assert store.is_stale(BIG_WINDOW) is True


def test_scale_to_resizes_templates_and_marks_source(store, tmp_path):
    store.window_size = (1920, 1080)
    store.add("search_btn", button(330, 50), RelRect(0.741, 0.823, 0.171, 0.045), "manual")
    store.save()

    store.scale_to(BIG_WINDOW)

    scaled = Image.open(store.template_path("search_btn"))
    assert scaled.size == (440, 67)          # 330*4/3, 50*4/3
    assert store.element("search_btn").source == "scaled"
    assert store.window_size == (2560, 1440)
    assert store.is_stale(BIG_WINDOW) is False


def test_foreign_format_version_is_discarded(tmp_path):
    directory = tmp_path / "calibration"
    directory.mkdir()
    (directory / "calibration.json").write_text(
        json.dumps({"version": 999, "window": {"width": 1, "height": 1},
                    "elements": {"search_btn": {"file": "x.png",
                                                "rect": {"x": 0, "y": 0, "w": 1, "h": 1},
                                                "source": "manual",
                                                "captured_at": "2026-01-01T00:00:00"}}}),
        encoding="utf-8"
    )

    store = cal.Calibration.load(directory)

    assert store.is_empty() is True


def test_broken_json_does_not_crash(tmp_path):
    directory = tmp_path / "calibration"
    directory.mkdir()
    (directory / "calibration.json").write_text("{ не json", encoding="utf-8")

    assert cal.Calibration.load(directory).is_empty() is True
```

- [ ] **Step 2: Запустити тест і переконатися, що він падає**

Run: `python -m pytest tests/test_calibration.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'calibration'`

- [ ] **Step 3: Написати мінімальну реалізацію**

```python
# calibration.py
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
```

- [ ] **Step 4: Запустити тести**

Run: `python -m pytest tests/test_calibration.py -v && python -m pytest tests -q`
Expected: усі PASS

- [ ] **Step 5: Закомітити**

```bash
git add calibration.py tests/test_calibration.py
git commit -m "$(cat <<'EOF'
Add calibration store

Templates are cropped from the user's own client, so the language and the UI
scale live in the data instead of being guessed. Positions are kept as
fractions of the window, which is what lets a remembered button survive a
resolution change: the templates are rescaled and re-saved rather than
thrown away.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Синтетичні макети та крос-конфігураційні тести

**Files:**
- Create: `tests/mock_dota.py`
- Create: `tests/test_recognition_scaling.py`

**Interfaces:**
- Consumes: `find_template`, `find_green_button` з `image_recognition`; `Calibration` з `calibration`; `WindowInfo`, `to_relative` з `dota_window`
- Produces: `render_menu(width, height, language, ui_scale) -> tuple[Image, dict[str, tuple]]`, `render_ready_popup(width, height, language) -> tuple[Image, dict[str, tuple]]`, `render_noisy_menu(width, height) -> Image`

Це шар, який доводить математику масштабування. Він **не** доводить, що справжня Dota виглядає як макет.

- [ ] **Step 1: Написати генератор макетів**

```python
# tests/mock_dota.py
# -*- coding: utf-8 -*-
"""Синтетичні макети інтерфейсу Dota для тестів розпізнавання."""
from PIL import Image, ImageDraw, ImageFont

LABELS = {
    "ru": {"search": "ПОИСК ИГРЫ", "searching": "ПОИСК МАТЧА", "accept": "ПРИНЯТЬ"},
    "en": {"search": "FIND MATCH", "searching": "SEARCHING", "accept": "ACCEPT"},
    "uk": {"search": "ПОШУК ГРИ", "searching": "ПОШУК МАТЧУ", "accept": "ПРИЙНЯТИ"},
}


def _font(size):
    for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _scaled(width, height, ui_scale):
    """Базові розміри елементів для вікна цього розміру."""
    unit = height / 1080 * ui_scale
    return {
        "button": (round(330 * unit), round(50 * unit)),
        "text": max(8, round(22 * unit)),
    }


def render_menu(width=1920, height=1080, language="ru", ui_scale=1.0):
    """Головне меню з кнопкою пошуку гри. Повертає (зображення, місця елементів)."""
    image = Image.new("RGB", (width, height), (24, 26, 28))
    draw = ImageDraw.Draw(image)
    sizes = _scaled(width, height, ui_scale)
    bw, bh = sizes["button"]

    draw.rectangle([0, 0, width, round(height * 0.12)], fill=(18, 20, 22))

    x = round(width * 0.74)
    y = round(height * 0.82)
    draw.rectangle([x, y, x + bw, y + bh], fill=(58, 110, 48))
    draw.text((x + bw // 2, y + bh // 2), LABELS[language]["search"],
              font=_font(sizes["text"]), fill=(255, 255, 255), anchor="mm")

    return image, {"search_btn": (x, y, bw, bh)}


def render_searching(width=1920, height=1080, language="ru", ui_scale=1.0):
    """Екран активного пошуку: індикатор і кнопка відміни."""
    image = Image.new("RGB", (width, height), (24, 26, 28))
    draw = ImageDraw.Draw(image)
    sizes = _scaled(width, height, ui_scale)
    bw, bh = sizes["button"]

    ix, iy = round(width * 0.42), round(height * 0.80)
    draw.rectangle([ix, iy, ix + bw, iy + bh], fill=(40, 44, 52))
    draw.text((ix + bw // 2, iy + bh // 2), LABELS[language]["searching"],
              font=_font(sizes["text"]), fill=(220, 220, 220), anchor="mm")

    sx, sy = round(width * 0.74), round(height * 0.82)
    side = bh
    draw.rectangle([sx, sy, sx + side, sy + side], fill=(150, 50, 45))

    return image, {"searching": (ix, iy, bw, bh), "stop": (sx, sy, side, side)}


def render_ready_popup(width=1920, height=1080, language="ru"):
    """Вікно прийняття матчу з зеленою кнопкою."""
    image = Image.new("RGB", (width, height), (24, 26, 28))
    draw = ImageDraw.Draw(image)
    unit = height / 1080

    draw.rectangle([round(width * 0.33), round(height * 0.22),
                    round(width * 0.67), round(height * 0.74)],
                   fill=(30, 33, 36), outline=(96, 168, 96), width=max(1, round(3 * unit)))

    bw, bh = round(520 * unit), round(65 * unit)
    x = round(width / 2 - bw / 2)
    y = round(height * 0.35)
    draw.rectangle([x, y, x + bw, y + bh], fill=(62, 123, 54))
    draw.text((x + bw // 2, y + bh // 2), LABELS[language]["accept"],
              font=_font(round(30 * unit)), fill=(255, 255, 255), anchor="mm")

    return image, {"accept": (x, y, bw, bh)}


def render_noisy_menu(width=1920, height=1080):
    """Меню без потрібних кнопок: портрети, банери, зелений текст."""
    image = Image.new("RGB", (width, height), (24, 26, 28))
    draw = ImageDraw.Draw(image)

    for i in range(8):
        x = round(width * 0.05) + i * round(width * 0.11)
        draw.rectangle([x, round(height * 0.3), x + round(width * 0.09),
                        round(height * 0.55)], fill=(46, 60, 44))

    draw.rectangle([0, round(height * 0.86), round(width * 0.14), height],
                   fill=(34, 70, 40))
    draw.text((round(width * 0.5), round(height * 0.2)), "Обновление доступно",
              font=_font(round(height / 1080 * 26)), fill=(120, 200, 120), anchor="mm")

    return image
```

- [ ] **Step 2: Написати крос-конфігураційні тести**

```python
# tests/test_recognition_scaling.py
# -*- coding: utf-8 -*-
"""Калібрування знято на одній конфігурації — розпізнавання йде на іншій."""
import pytest

import calibration as cal
import image_recognition as ir
import mock_dota
from dota_window import WindowInfo, to_relative

CONFIGS = [
    (1920, 1080), (2560, 1440), (1366, 768), (3440, 1440),
]


def window(width, height, left=0, top=0):
    return WindowInfo(left, top, width, height, "Dota 2")


def calibrate(tmp_path, frame, rects, win, name="search_btn"):
    """Зняти шаблон з кадру так само, як це зробить майстер."""
    store = cal.Calibration.load(tmp_path / "calibration")
    store.window_size = (win.width, win.height)
    x, y, w, h = rects[name]
    crop = frame.crop((x, y, x + w, y + h))
    store.add(name, crop, to_relative(win, (win.left + x, win.top + y, w, h)), "manual")
    store.save()
    return store


@pytest.mark.parametrize("width,height", CONFIGS)
@pytest.mark.parametrize("language", ["ru", "en", "uk"])
def test_calibrated_button_is_found_on_its_own_config(tmp_path, width, height, language):
    win = window(width, height)
    frame, rects = mock_dota.render_menu(width, height, language)
    store = calibrate(tmp_path, frame, rects, win)

    region = store.search_region("search_btn", win)
    crop = frame.crop((region[0], region[1], region[0] + region[2], region[1] + region[3]))
    box = ir.find_template(store.template_path("search_btn"), crop,
                           confidence=0.9, offset=region[:2])

    assert box is not None
    assert abs(box.left - rects["search_btn"][0]) <= 2


@pytest.mark.parametrize("width,height", [(2560, 1440), (1366, 768), (3440, 1440)])
def test_scaled_calibration_survives_resolution_change(tmp_path, width, height):
    """Знято на 1080p, застосовано на іншому розмірі після scale_to."""
    small = window(1920, 1080)
    frame, rects = mock_dota.render_menu(1920, 1080)
    store = calibrate(tmp_path, frame, rects, small)

    big = window(width, height)
    assert store.is_stale(big) is True
    store.scale_to(big)

    target, target_rects = mock_dota.render_menu(width, height)
    region = store.search_region("search_btn", big)
    crop = target.crop((region[0], region[1], region[0] + region[2], region[1] + region[3]))
    box = ir.find_template(store.template_path("search_btn"), crop,
                           confidence=0.75, offset=region[:2])

    assert box is not None, f"шаблон не знайшовся після масштабування до {width}x{height}"
    assert abs(box.left - target_rects["search_btn"][0]) <= 6


@pytest.mark.parametrize("ui_scale", [0.85, 1.15])
def test_ui_scale_change_is_detected_as_mismatch(tmp_path, ui_scale):
    """Повзунок масштабу UI не змінює розмір вікна — шаблон просто не знайдеться."""
    win = window(1920, 1080)
    frame, rects = mock_dota.render_menu(1920, 1080)
    store = calibrate(tmp_path, frame, rects, win)

    rescaled, _ = mock_dota.render_menu(1920, 1080, ui_scale=ui_scale)
    region = store.search_region("search_btn", win)
    crop = rescaled.crop((region[0], region[1], region[0] + region[2], region[1] + region[3]))

    assert ir.find_template(store.template_path("search_btn"), crop,
                            confidence=0.9, offset=region[:2]) is None


@pytest.mark.parametrize("width,height", CONFIGS)
def test_accept_button_found_by_colour_on_any_config(width, height):
    frame, rects = mock_dota.render_ready_popup(width, height)

    box = ir.find_green_button(frame)

    assert box is not None
    x, y, w, h = rects["accept"]
    assert abs(box.left - x) <= 4 and abs(box.width - w) <= 8


@pytest.mark.parametrize("language", ["ru", "en", "uk"])
def test_accept_colour_search_ignores_language(language):
    frame, rects = mock_dota.render_ready_popup(1920, 1080, language)

    box = ir.find_green_button(frame)

    assert box is not None
    assert abs(box.left - rects["accept"][0]) <= 4


@pytest.mark.parametrize("width,height", CONFIGS)
def test_no_false_positives_on_noisy_menu(width, height):
    assert ir.find_green_button(mock_dota.render_noisy_menu(width, height)) is None
```

- [ ] **Step 3: Запустити тести**

Run: `python -m pytest tests/test_recognition_scaling.py -v`
Expected: усі PASS. Якщо `test_ui_scale_change_is_detected_as_mismatch` не проходить при 0.85 — це означає, що поріг 0.9 надто м'який; **не послаблювати тест**, а зафіксувати фактичний поріг у `config.CONFIDENCE` і в коментарі до тесту.

- [ ] **Step 4: Переконатися, що решта тестів не зламалась**

Run: `python -m pytest tests -q`
Expected: усі PASS

- [ ] **Step 5: Закомітити**

```bash
git add tests/mock_dota.py tests/test_recognition_scaling.py
git commit -m "$(cat <<'EOF'
Add synthetic multi-config recognition tests

There is no second machine to test on, so the scaling maths is proven
against rendered mock menus at four resolutions, three client languages and
two UI scales, plus a noisy menu that must yield nothing. These prove our
algorithms, not that real Dota looks like the mocks; the manual matrix
covers that.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Цикл на вікні Dota і стан NO_GAME

**Files:**
- Modify: `dota_helper.py:14-15` (імпорти), `dota_helper.py:21-25` (`State`), `dota_helper.py:44` (`accept_region`), `dota_helper.py:219` (`run`)
- Modify: `config.py:68-73` (прибрати `SEARCH_REGION`, `ACCEPT_REGION_*`, додати `CALIBRATION_DIR`, `NO_GAME_POLL_INTERVAL`)
- Modify: `telegram_bot.py` (`_build_menu`, `_menu_text`)
- Modify: `image_recognition.py` (прибрати `get_center_region` і `find_green_button_on_screen`)
- Modify: `tests/test_accept_detection.py` (прибрати `test_center_region_is_clamped_to_screen`)
- Test: `tests/test_dota_helper_states.py`

**Interfaces:**
- Consumes: `dota_window.find_window/is_usable/capture/to_relative`, `calibration.Calibration`, `image_recognition.find_template/find_green_button`
- Produces: `State.NO_GAME`, `DotaHelper(telegram_bot, calibration=None)`, `DotaHelper.locate(name, window, frame) -> Optional[Box]`

Один знімок вікна за ітерацію замість трьох повноекранних.

- [ ] **Step 1: Написати тест, що падає**

```python
# tests/test_dota_helper_states.py
# -*- coding: utf-8 -*-
"""Поведінка циклу залежно від наявності вікна Dota і калібрування."""
import pytest

import calibration as cal
import dota_helper as dh
import mock_dota
from dota_window import WindowInfo, to_relative


class FakeBot:
    def __init__(self):
        self.messages = []
        self.menus = []

    def send_message(self, text):
        self.messages.append(text)

    def send_menu(self, state):
        self.menus.append(state)


@pytest.fixture
def helper(tmp_path, monkeypatch):
    monkeypatch.setattr(dh, "Statistics", lambda *a, **kw: _FakeStats())
    store = cal.Calibration.load(tmp_path / "calibration")
    return dh.DotaHelper(FakeBot(), calibration=store)


class _FakeStats:
    def __init__(self):
        self.accepted = 0

    def start_search(self):
        pass

    def match_accepted(self):
        self.accepted += 1

    def match_missed(self):
        pass

    def get_summary(self):
        return {"today_accepted": 0, "total_matches_accepted": 0}

    def get_formatted_summary(self):
        return ""


def test_no_window_switches_to_no_game(helper, monkeypatch):
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: None)

    helper.tick()

    assert helper.state is dh.State.NO_GAME


def test_minimized_window_is_treated_as_no_game(helper, monkeypatch):
    minimized = WindowInfo(-32000, -32000, 1920, 1080, "Dota 2")
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: minimized)

    helper.tick()

    assert helper.state is dh.State.NO_GAME


def test_start_search_without_calibration_explains_itself(helper, monkeypatch):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, _ = mock_dota.render_menu()
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)
    helper.pending_start = True

    helper.tick()

    assert any("калібрув" in m.lower() for m in helper.telegram_bot.messages)


def test_accept_is_found_without_any_calibration(helper, monkeypatch):
    """Приймання матчу працює навіть коли калібрування пропущено."""
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, rects = mock_dota.render_ready_popup()
    clicked = []
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)
    monkeypatch.setattr(dh, "click_center", lambda box, **kw: clicked.append(box) or True)

    helper.tick()

    assert helper.state is dh.State.READY
    assert clicked and abs(clicked[0].left - rects["accept"][0]) <= 4


def test_single_capture_per_tick(helper, monkeypatch):
    """Знімок вікна робиться один раз, а не окремо для кожної перевірки."""
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, _ = mock_dota.render_menu()
    captures = []
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture",
                        lambda w: captures.append(w) or frame)

    helper.tick()

    assert len(captures) == 1
```

- [ ] **Step 2: Запустити тест і переконатися, що він падає**

Run: `python -m pytest tests/test_dota_helper_states.py -v`
Expected: FAIL — `AttributeError: module 'dota_helper' has no attribute 'dota_window'`

- [ ] **Step 3: Переписати dota_helper**

```python
# dota_helper.py — імпорти та стан
import dota_window
from calibration import Calibration, ELEMENTS
from config import (
    CONFIDENCE, SCAN_INTERVAL, MESSAGE_COOLDOWN,
    CALIBRATION_DIR, NO_GAME_POLL_INTERVAL, ACCEPT_COLOR_FALLBACK
)
from image_recognition import (
    find_template, find_green_button, click_center, double_click_center
)

class State(Enum):
    """Стани бота."""
    NO_GAME = "no_game"
    IDLE = "idle"
    SEARCHING = "searching"
    READY = "ready"
```

```python
# dota_helper.py — конструктор
    def __init__(self, telegram_bot, calibration=None):
        self.telegram_bot = telegram_bot
        self.running = True
        self.paused = False
        self.state = State.NO_GAME
        self.last_message_time = {}

        self.pending_start = False
        self.pending_stop = False
        self.pending_stats = False
        self.pending_export = False

        self.calibration = calibration or Calibration.load(CALIBRATION_DIR)
        self.stats = Statistics()
        self.exporter = ReportExporter(self.stats)
```

```python
# dota_helper.py — пошук елемента у знятому кадрі
    def locate(self, name, window, frame):
        """
        Знайти елемент у вже знятому кадрі вікна.

        Для "accept" працює пошук за кольором навіть без калібрування.
        """
        if self.calibration.has(name):
            region = self.calibration.search_region(name, window)
            crop = frame.crop((
                region[0] - window.left, region[1] - window.top,
                region[0] - window.left + region[2],
                region[1] - window.top + region[3],
            ))
            box = find_template(
                self.calibration.template_path(name), crop,
                confidence=CONFIDENCE.get(name, 0.8), offset=region[:2]
            )
            if box:
                return box

        if name == "accept" and ACCEPT_COLOR_FALLBACK:
            return find_green_button(frame, offset=(window.left, window.top))

        return None

    def tick(self):
        """Одна ітерація циклу. Повертає паузу до наступної."""
        window = dota_window.find_window()
        if not dota_window.is_usable(window):
            self._set_state(State.NO_GAME)
            self._answer_pending_without_game()
            return NO_GAME_POLL_INTERVAL

        frame = dota_window.capture(window)

        if self.pending_start:
            self.pending_start = False
            self._handle_start(window, frame)
            return 0.6

        if self.pending_stop:
            self.pending_stop = False
            self._handle_stop(window, frame)
            return 0.6

        if self.pending_stats:
            self.pending_stats = False
            self.telegram_bot.send_message(self.stats.get_formatted_summary())
            return 0.3

        if self.pending_export:
            self.pending_export = False
            self._handle_export()
            return 0.3

        if self.check_accept_button(window, frame):
            return 1.0

        if self.locate("searching", window, frame):
            if self.state is not State.SEARCHING:
                self._set_state(State.SEARCHING)
                self._debounced_message("🔎 Пошук гри активний.")
                self.stats.start_search()
            return SCAN_INTERVAL

        if self.locate("search_btn", window, frame):
            self._set_state(State.IDLE)

        return SCAN_INTERVAL

    def run(self):
        """Основний цикл моніторингу."""
        logger.info("🟢 Dota Ready Helper запущено")
        logger.info("Гарячі клавіші: F6 — пауза, F7 — вихід, F8 — старт, F9 — стоп")
        self._debounced_message("🟢 Dota Ready Helper запущено.")
        self.telegram_bot.send_menu(self.state.value)

        while self.running:
            if self.paused:
                time.sleep(0.3)
                continue
            time.sleep(self.tick())

        logger.info("🔴 Dota Ready Helper зупинено")
```

```python
# dota_helper.py — допоміжні методи
    def _answer_pending_without_game(self):
        """Пояснити, чому команда не виконується, поки Dota не запущена."""
        if self.pending_start or self.pending_stop:
            self.pending_start = self.pending_stop = False
            self._debounced_message("⚠️ Dota 2 не запущена.")

    def _needs_calibration(self, name) -> bool:
        if self.calibration.has(name):
            return False
        self._debounced_message(
            "⚠️ Потрібне калібрування: запусти `python main.py --calibrate`.\n"
            "Приймання матчів працює й без нього."
        )
        return True

    def _handle_start(self, window, frame):
        if self._needs_calibration("search_btn"):
            return
        button = self.locate("search_btn", window, frame)
        if not button:
            self._debounced_message(
                "⚠️ Не знайшов 'Пошук гри' на екрані.\n"
                "Відкрий головне меню Dota 2."
            )
            return
        double_click_center(button, interval=0.5)
        self._debounced_message("▶️ Пошук гри запущено.")
        self._set_state(State.SEARCHING)
        self.stats.start_search()

    def _handle_stop(self, window, frame):
        if self._needs_calibration("stop"):
            return
        button = self.locate("stop", window, frame)
        if not button:
            self._debounced_message("⚠️ Не знайшов кнопку 'Стоп'.")
            return
        click_center(button)
        self._debounced_message("⏹ Пошук гри зупинено.")
        self._set_state(State.IDLE)

    def _handle_export(self):
        with ErrorHandler("Експорт звітів", self.telegram_bot, silent=True):
            export_dir = Path(__file__).parent / "exports"
            results = self.exporter.export_all(export_dir)
            self.telegram_bot.send_message(
                f"📥 Експорт завершено!\n\nУспішно: {sum(results.values())}/4 форматів"
            )

    def check_accept_button(self, window, frame) -> bool:
        """Знайти кнопку 'Прийняти' у кадрі та натиснути її."""
        accept = self.locate("accept", window, frame)
        if not accept:
            return False

        if self.state is not State.READY:
            self._set_state(State.READY)
            self._debounced_message("✅ Гра знайдена! Натискаю 'Прийняти'...")

            if not click_center(accept):
                self.stats.match_missed()
                self._debounced_message(
                    "⚠️ Не вдалося натиснути 'Прийняти'. Прийми матч вручну!"
                )
                return True

            self.stats.match_accepted()
            summary = self.stats.get_summary()
            self._debounced_message(
                f"🎮 Гру прийнято!\n\n"
                f"📊 Сьогодні прийнято: {summary['today_accepted']}\n"
                f"📈 Всього: {summary['total_matches_accepted']}"
            )
        return True
```

У `config.py` замінити рядки 68-73:

```python
# Калібрування
CALIBRATION_DIR = BASE_DIR / "calibration"

# Пауза між перевірками, коли Dota не запущена
NO_GAME_POLL_INTERVAL = _env_float("NO_GAME_POLL_INTERVAL", 2.0)
```

`CONFIDENCE` доповнити ключами під імена елементів:

```python
CONFIDENCE = {
    "accept": _env_float("CONFIDENCE_ACCEPT", 0.80),
    "searching": _env_float("CONFIDENCE_SEARCHING", 0.70),
    "search_btn": _env_float("CONFIDENCE_SEARCH_BTN", 0.70),
    "stop": _env_float("CONFIDENCE_STOP_BTN", 0.75),
}
```

У `telegram_bot.py` додати стан у меню:

```python
    def _build_menu(self, state: str) -> types.InlineKeyboardMarkup:
        kb = types.InlineKeyboardMarkup()
        if state == "no_game":
            return kb
        if state == "searching":
            kb.add(types.InlineKeyboardButton("⏹ Зупинити пошук",
                                              callback_data="stop_search"))
        else:
            kb.add(types.InlineKeyboardButton("🔁 Запустити пошук",
                                              callback_data="start_search"))
        return kb

    def _menu_text(self, state: str) -> str:
        if state == "no_game":
            return "🎮 Dota 2 не запущена.\nЗапусти гру — меню з'явиться саме."
        if state == "searching":
            return ("🔎 Пошук гри активний.\n"
                    "Бот автоматично натисне «Прийняти» при знаходженні матчу.")
        if state == "ready":
            return "✅ Матч знайдено!\nНатискаю «Прийняти»..."
        return "⏹ Пошук не активний.\nМожеш запустити пошук гри."
```

З `image_recognition.py` прибрати `get_center_region`, `find_green_button_on_screen`, `find_on_screen` і блок `if __name__ == "__main__"` — знімок екрана більше не робиться в цьому модулі. З `tests/test_accept_detection.py` прибрати `test_center_region_is_clamped_to_screen`.

- [ ] **Step 4: Запустити всі тести**

Run: `python -m pytest tests -q`
Expected: усі PASS (кількість зменшиться на 1 через прибраний тест `get_center_region`)

- [ ] **Step 5: Закомітити**

```bash
git add dota_helper.py config.py telegram_bot.py image_recognition.py tests/
git commit -m "$(cat <<'EOF'
Drive the monitoring loop from the Dota window

Every check now runs against a single capture of the Dota 2 window instead
of up to three full-screen grabs per iteration, which also fixes the
multi-monitor case where the primary screen is not where the game is. A
NO_GAME state stops the scanning entirely while the game is closed, and
commands that need calibration say so instead of reporting a missing button.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Самокалібрування кнопки «Прийняти»

**Files:**
- Modify: `dota_helper.py` (`check_accept_button`)
- Test: `tests/test_dota_helper_states.py`

**Interfaces:**
- Consumes: `Calibration.add`, `dota_window.to_relative`
- Produces: нічого нового; після першого спійманого матчу у калібруванні з'являється елемент `accept` з `source="opportunistic"`

Попап прийняття неможливо викликати на замовлення, тому шаблон знімається з першого ж реального матчу.

- [ ] **Step 1: Написати тест, що падає**

```python
# додати в tests/test_dota_helper_states.py
def test_accept_is_learned_from_the_first_match(helper, monkeypatch):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, rects = mock_dota.render_ready_popup()
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)
    monkeypatch.setattr(dh, "click_center", lambda box, **kw: True)

    helper.tick()

    element = helper.calibration.element("accept")
    assert element is not None
    assert element.source == "opportunistic"
    assert helper.calibration.template_path("accept").exists()
    assert element.rect.x == pytest.approx(rects["accept"][0] / 1920, abs=0.01)


def test_accept_is_not_relearned_when_already_calibrated(helper, monkeypatch):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, rects = mock_dota.render_ready_popup()
    x, y, w, h = rects["accept"]
    helper.calibration.window_size = (1920, 1080)
    helper.calibration.add("accept", frame.crop((x, y, x + w, y + h)),
                           to_relative(window, (x, y, w, h)), "manual")
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)
    monkeypatch.setattr(dh, "click_center", lambda box, **kw: True)

    helper.tick()

    assert helper.calibration.element("accept").source == "manual"
```

- [ ] **Step 2: Запустити тест і переконатися, що він падає**

Run: `python -m pytest tests/test_dota_helper_states.py -k learned -v`
Expected: FAIL — `AssertionError: assert None is not None`

- [ ] **Step 3: Додати самокалібрування**

```python
# dota_helper.py — у check_accept_button, одразу після успішного кліку
            self.stats.match_accepted()
            self._learn_accept(window, frame, accept)
```

```python
# dota_helper.py — новий метод
    def _learn_accept(self, window, frame, box):
        """
        Запам'ятати кнопку 'Прийняти' з першого спійманого матчу.

        Показати цей попап на вимогу неможливо, тому шаблон знімається
        під час реальної гри й далі працює точний збіг.
        """
        if self.calibration.has("accept"):
            return

        with ErrorHandler("Самокалібрування 'Прийняти'", silent=True):
            local = (box.left - window.left, box.top - window.top)
            crop = frame.crop((local[0], local[1],
                               local[0] + box.width, local[1] + box.height))

            if not self.calibration.window_size:
                self.calibration.window_size = (window.width, window.height)

            self.calibration.add(
                "accept", crop,
                dota_window.to_relative(window, (box.left, box.top,
                                                 box.width, box.height)),
                "opportunistic"
            )
            self.calibration.save()
```

- [ ] **Step 4: Запустити тести**

Run: `python -m pytest tests -q`
Expected: усі PASS

- [ ] **Step 5: Закомітити**

```bash
git add dota_helper.py tests/test_dota_helper_states.py
git commit -m "$(cat <<'EOF'
Learn the accept button from the first caught match

The ready popup cannot be staged during calibration, so the colour detector
catches it once and the button is cropped and stored as the user's own
template. From the second match on, matching is exact and the colour search
is only a fallback.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Автопідказка майстра

**Files:**
- Create: `calibration_wizard.py` (лише чисті функції на цьому кроці)
- Test: `tests/test_calibration_wizard.py`

**Interfaces:**
- Consumes: `image_recognition.find_template/find_green_button`, `config.IMG_ACCEPT_VARIANTS`, `config.ASSETS_DIR`
- Produces: `SCALES`, `detect_candidates(frame, templates, confidence=0.7) -> list[Box]`, `shipped_templates(name) -> list[Path]`, `is_blank(frame) -> bool`

- [ ] **Step 1: Написати тест, що падає**

```python
# tests/test_calibration_wizard.py
# -*- coding: utf-8 -*-
"""Автопідказка та перевірки майстра калібрування."""
import pytest
from PIL import Image

import calibration_wizard as wiz
import mock_dota


def test_finds_shipped_template_at_native_scale(tmp_path):
    frame, rects = mock_dota.render_menu(1920, 1080)
    x, y, w, h = rects["search_btn"]
    template = tmp_path / "search_game.png"
    frame.crop((x, y, x + w, y + h)).save(template)

    candidates = wiz.detect_candidates(frame, [template])

    assert candidates
    assert abs(candidates[0].left - x) <= 2


def test_finds_shipped_template_at_another_scale(tmp_path):
    """Шаблон знято на 1080p, кадр — на 1440p."""
    small, small_rects = mock_dota.render_menu(1920, 1080)
    x, y, w, h = small_rects["search_btn"]
    template = tmp_path / "search_game.png"
    small.crop((x, y, x + w, y + h)).save(template)

    frame, rects = mock_dota.render_menu(2560, 1440)
    candidates = wiz.detect_candidates(frame, [template], confidence=0.75)

    assert candidates
    assert abs(candidates[0].left - rects["search_btn"][0]) <= 10


def test_no_candidates_on_noisy_menu(tmp_path):
    small, small_rects = mock_dota.render_menu(1920, 1080)
    x, y, w, h = small_rects["search_btn"]
    template = tmp_path / "search_game.png"
    small.crop((x, y, x + w, y + h)).save(template)

    assert wiz.detect_candidates(mock_dota.render_noisy_menu(), [template]) == []


def test_candidates_are_deduplicated(tmp_path):
    """Той самий елемент, знайдений на кількох масштабах, — один кандидат."""
    frame, rects = mock_dota.render_menu(1920, 1080)
    x, y, w, h = rects["search_btn"]
    template = tmp_path / "a.png"
    frame.crop((x, y, x + w, y + h)).save(template)
    second = tmp_path / "b.png"
    frame.crop((x, y, x + w, y + h)).save(second)

    assert len(wiz.detect_candidates(frame, [template, second])) == 1


@pytest.mark.parametrize("colour,expected", [
    ((0, 0, 0), True),
    ((3, 3, 3), True),
    ((24, 26, 28), False),
])
def test_is_blank_detects_black_capture(colour, expected):
    """Ексклюзивний повноекранний режим дає чорний знімок."""
    assert wiz.is_blank(Image.new("RGB", (800, 600), colour)) is expected


def test_menu_frame_is_not_blank():
    frame, _ = mock_dota.render_menu()
    assert wiz.is_blank(frame) is False
```

- [ ] **Step 2: Запустити тест і переконатися, що він падає**

Run: `python -m pytest tests/test_calibration_wizard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'calibration_wizard'`

- [ ] **Step 3: Написати чисту частину майстра**

```python
# calibration_wizard.py
# -*- coding: utf-8 -*-
"""Майстер калібрування: зняти мірки кнопок з клієнта користувача."""
from pathlib import Path
from typing import List, Optional

import numpy as np
from PIL import Image

from config import ASSETS_DIR, CONFIDENCE
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

def detect_candidates(frame: Image.Image, templates: List[Path],
                      confidence: Optional[float] = None) -> List[Box]:
    """
    Знайти на кадрі місця, схожі на кнопку.

    Шаблони перебираються в діапазоні масштабів, бо розмір інтерфейсу
    користувача заздалегідь невідомий.
    """
    conf = confidence if confidence is not None else 0.7
    found: List[Box] = []

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

            box = find_template(needle.resize(size, Image.LANCZOS), frame,
                                confidence=conf)
            if box and not any(_overlaps(box, existing) for existing in found):
                found.append(box)

    return found

def detect_accept(frame: Image.Image) -> Optional[Box]:
    """Кнопку 'Прийняти' шукаємо за кольором — вона не залежить від мови."""
    return find_green_button(frame)
```

- [ ] **Step 4: Запустити тести**

Run: `python -m pytest tests/test_calibration_wizard.py -v && python -m pytest tests -q`
Expected: усі PASS

- [ ] **Step 5: Закомітити**

```bash
git add calibration_wizard.py tests/test_calibration_wizard.py
git commit -m "$(cat <<'EOF'
Add auto-detection for the calibration wizard

The shipped templates are tried across a range of scales so a user whose
client is larger or smaller than the author's still gets a pre-filled
suggestion to confirm, and overlapping hits from several scales collapse
into one candidate. A blankness check catches exclusive fullscreen, where
the capture comes back black.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Вікно майстра калібрування

**Files:**
- Modify: `calibration_wizard.py`
- Test: `tests/test_calibration_wizard.py`

**Interfaces:**
- Consumes: `detect_candidates`, `is_blank`, `dota_window`, `Calibration`
- Produces: `CropLabel` (віджет виділення рамкою), `run_wizard(calibration_dir=None) -> bool`, `CAPTURE_HOTKEY = "F10"`

Вікно майстра і вікно Dota не можуть бути на передньому плані одночасно, тому знімок робиться глобальною клавішею F10.

- [ ] **Step 1: Написати тест, що падає**

```python
# додати в tests/test_calibration_wizard.py
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qt_app():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_crop_label_maps_selection_back_to_frame(qt_app):
    """Рамка малюється на зменшеному знімку, а координати потрібні справжні."""
    from PyQt6.QtCore import QPoint

    frame, _ = mock_dota.render_menu(1920, 1080)
    label = wiz.CropLabel()
    label.set_frame(frame, display_width=960)

    label.begin_selection(QPoint(100, 200))
    label.update_selection(QPoint(200, 250))
    rect = label.finish_selection(QPoint(200, 250))

    assert rect == (200, 400, 200, 100)


def test_crop_label_rejects_tiny_selection(qt_app):
    from PyQt6.QtCore import QPoint

    frame, _ = mock_dota.render_menu(1920, 1080)
    label = wiz.CropLabel()
    label.set_frame(frame, display_width=960)

    label.begin_selection(QPoint(100, 100))
    assert label.finish_selection(QPoint(102, 101)) is None
```

- [ ] **Step 2: Запустити тест і переконатися, що він падає**

Run: `python -m pytest tests/test_calibration_wizard.py -k crop_label -v`
Expected: FAIL — `AttributeError: module 'calibration_wizard' has no attribute 'CropLabel'`

- [ ] **Step 3: Написати віджет і потік майстра**

```python
# calibration_wizard.py — додати
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QVBoxLayout
)

CAPTURE_HOTKEY = "F10"

# Найменша рамка, яку вважаємо кнопкою
MIN_SELECTION = 10

class CropLabel(QLabel):
    """Знімок вікна з можливістю виділити кнопку рамкою."""

    def __init__(self):
        super().__init__()
        self.frame: Optional[Image.Image] = None
        self.ratio = 1.0
        self._start: Optional[QPoint] = None
        self._current: Optional[QPoint] = None
        self.highlight: Optional[tuple] = None

    def set_frame(self, frame: Image.Image, display_width: int = 960):
        """Показати кадр, зменшений до display_width."""
        self.frame = frame
        self.ratio = frame.width / display_width
        height = round(frame.height / self.ratio)

        image = QImage(frame.convert("RGB").tobytes(), frame.width, frame.height,
                       frame.width * 3, QImage.Format.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(image).scaled(display_width, height,
                                                       Qt.AspectRatioMode.KeepAspectRatio))
        self.setFixedSize(display_width, height)

    def begin_selection(self, point: QPoint):
        self._start = point
        self._current = point

    def update_selection(self, point: QPoint):
        self._current = point
        self.update()

    def finish_selection(self, point: QPoint) -> Optional[tuple]:
        """Повернути виділене у координатах справжнього кадру."""
        if self._start is None:
            return None

        left, top = min(self._start.x(), point.x()), min(self._start.y(), point.y())
        width, height = abs(point.x() - self._start.x()), abs(point.y() - self._start.y())
        self._start = self._current = None

        if width < MIN_SELECTION or height < MIN_SELECTION:
            return None

        return (round(left * self.ratio), round(top * self.ratio),
                round(width * self.ratio), round(height * self.ratio))

    def mousePressEvent(self, event):
        self.begin_selection(event.pos())

    def mouseMoveEvent(self, event):
        self.update_selection(event.pos())

    def mouseReleaseEvent(self, event):
        rect = self.finish_selection(event.pos())
        if rect:
            self.highlight = rect
            self.selected(rect)

    def selected(self, rect):
        """Перевизначається діалогом."""

    def paintEvent(self, event):
        super().paintEvent(event)
        if not (self._start and self._current):
            return

        painter = QPainter(self)
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.drawRect(QRect(self._start, self._current))
```

Далі — діалог: три кроки (`main_menu`, `searching`, `summary`), глобальна клавіша `keyboard.add_hotkey(CAPTURE_HOTKEY, ...)`, підтвердження автокандидата, ручне виділення через `CropLabel`, кнопка «Перевірити зараз», кнопка «Пропустити». Діалог зберігає результат у `Calibration` і повертає `True`, якщо щось збережено.

```python
def run_wizard(calibration_dir=None) -> bool:
    """
    Показати майстер калібрування.

    Returns:
        True якщо калібрування збережено (навіть частково)
    """
    from config import CALIBRATION_DIR

    store = Calibration.load(calibration_dir or CALIBRATION_DIR)
    app = QApplication.instance() or QApplication([])
    dialog = _WizardDialog(store)
    dialog.exec()
    return dialog.saved
```

Повний текст `_WizardDialog` пишеться на цьому кроці за схемою зі специфікації, розділ 5: очікування вікна Dota (таймер 2 с), підказка з F10, знімок → `is_blank` → попередження про ексклюзивний режим, автопідказка → підтвердження або ручна рамка, другий кадр для `searching` і `stop`, зведення, «Перевірити зараз», «Пропустити».

- [ ] **Step 4: Перевірити майстер на макеті, не показуючи вікон**

Створити `tests/test_calibration_wizard_flow.py`:

```python
# -*- coding: utf-8 -*-
"""Потік майстра без показу вікон: підміняємо знімок і підтвердження."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

import calibration_wizard as wiz
import mock_dota
from dota_window import WindowInfo


@pytest.fixture
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_wizard_saves_confirmed_candidate(qt_app, tmp_path, monkeypatch):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    menu, rects = mock_dota.render_menu()
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.dota_window, "capture", lambda w: menu)
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = wiz._WizardDialog(wiz.Calibration.load(tmp_path / "calibration"))
    dialog.capture_step("search_btn")
    dialog.confirm_candidate()
    dialog.save_and_close()

    element = dialog.store.element("search_btn")
    assert element is not None
    assert element.rect.x == pytest.approx(rects["search_btn"][0] / 1920, abs=0.01)


def test_wizard_warns_on_blank_capture(qt_app, tmp_path, monkeypatch):
    from PIL import Image

    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.dota_window, "capture",
                        lambda w: Image.new("RGB", (1920, 1080), (0, 0, 0)))
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = wiz._WizardDialog(wiz.Calibration.load(tmp_path / "calibration"))
    dialog.capture_step("search_btn")

    assert "оконн" in dialog.status.text().lower() or "рамк" in dialog.status.text().lower()
```

Run: `python -m pytest tests/test_calibration_wizard_flow.py -v && python -m pytest tests -q`
Expected: усі PASS

- [ ] **Step 5: Закомітити**

```bash
git add calibration_wizard.py tests/test_calibration_wizard.py tests/test_calibration_wizard_flow.py
git commit -m "$(cat <<'EOF'
Add the calibration wizard window

The wizard and Dota cannot both be in the foreground, so the capture is
triggered by a global F10 hotkey. Auto-detection pre-fills a candidate for
the user to confirm and a drag-to-select fallback covers the cases it
misses. The last step verifies itself against a fresh capture rather than
claiming success, and a Skip button leaves match accepting working.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Підключення майстра до запуску

**Files:**
- Modify: `main.py` (після `ensure_configured`)
- Modify: `README.md`, `QUICKSTART.md`
- Test: `tests/test_main_setup.py`

**Interfaces:**
- Consumes: `calibration_wizard.run_wizard`, `calibration.Calibration`, `dota_window.find_window`
- Produces: `ensure_calibrated(force_setup=False) -> Calibration`

- [ ] **Step 1: Написати тест, що падає**

```python
# додати в tests/test_main_setup.py
import calibration as cal
import calibration_wizard as wiz
from dota_window import WindowInfo


@pytest.fixture
def wizard_calls(monkeypatch, tmp_path):
    state = {"shown": 0, "result": True, "dir": tmp_path / "calibration"}

    def fake_wizard(calibration_dir=None):
        state["shown"] += 1
        return state["result"]

    monkeypatch.setattr(wiz, "run_wizard", fake_wizard)
    monkeypatch.setattr(main.config, "CALIBRATION_DIR", state["dir"])
    return state


def test_calibrated_user_does_not_see_the_wizard(wizard_calls, monkeypatch):
    store = cal.Calibration.load(wizard_calls["dir"])
    store.window_size = (1920, 1080)
    store.elements["search_btn"] = cal.Element("search_btn.png",
                                               cal.RelRect(0.1, 0.1, 0.1, 0.1),
                                               "manual", "2026-01-01T00:00:00")
    store.save()
    (wizard_calls["dir"] / "search_btn.png").write_bytes(b"")

    monkeypatch.setattr(main.dota_window, "find_window",
                        lambda: WindowInfo(0, 0, 1920, 1080, "Dota 2"))

    main.ensure_calibrated()

    assert wizard_calls["shown"] == 0


def test_wizard_runs_when_calibration_missing(wizard_calls, monkeypatch):
    monkeypatch.setattr(main.dota_window, "find_window", lambda: None)

    main.ensure_calibrated()

    assert wizard_calls["shown"] == 1


def test_skipped_calibration_does_not_block_startup(wizard_calls, monkeypatch):
    """Пропуск майстра лишає приймання матчів робочим."""
    wizard_calls["result"] = False
    monkeypatch.setattr(main.dota_window, "find_window", lambda: None)

    store = main.ensure_calibrated()

    assert store is not None
    assert store.is_empty() is True


def test_resolution_change_rescales_calibration(wizard_calls, monkeypatch):
    from PIL import Image

    store = cal.Calibration.load(wizard_calls["dir"])
    store.window_size = (1920, 1080)
    store.add("search_btn", Image.new("RGB", (330, 50), (58, 110, 48)),
              cal.RelRect(0.74, 0.82, 0.17, 0.046), "manual")
    store.save()

    monkeypatch.setattr(main.dota_window, "find_window",
                        lambda: WindowInfo(0, 0, 2560, 1440, "Dota 2"))

    result = main.ensure_calibrated()

    assert result.window_size == (2560, 1440)
    assert wizard_calls["shown"] == 0
```

- [ ] **Step 2: Запустити тест і переконатися, що він падає**

Run: `python -m pytest tests/test_main_setup.py -k calib -v`
Expected: FAIL — `AttributeError: module 'main' has no attribute 'ensure_calibrated'`

- [ ] **Step 3: Додати крок у main.py**

```python
# main.py — імпорти
import dota_window
from calibration import Calibration
```

```python
# main.py — новий крок
def ensure_calibrated(force_setup: bool = False) -> Calibration:
    """
    Переконатися, що калібрування придатне, за потреби показавши майстер.

    Returns:
        Калібрування — можливо порожнє, якщо майстер пропущено
    """
    store = Calibration.load(config.CALIBRATION_DIR)
    window = dota_window.find_window()

    if not force_setup and not store.is_empty():
        if window and store.is_stale(window):
            logger.info("Розмір вікна змінився — перераховую калібрування")
            store.scale_to(window)
        return store

    if not force_setup and not store.is_empty():
        return store

    from calibration_wizard import run_wizard

    if not run_wizard(config.CALIBRATION_DIR):
        logger.info(
            "Калібрування пропущено: приймання матчів працює, "
            "керування пошуком з Telegram — ні"
        )

    return Calibration.load(config.CALIBRATION_DIR)
```

```python
# main.py — у main(), після ensure_configured
    calibration = ensure_calibrated(force_setup="--calibrate" in sys.argv)
    ...
    helper = DotaHelper(telegram_bot, calibration=calibration)
```

У README (обидві мовні секції) і QUICKSTART додати розділ про калібрування: що воно робить, коли з'являється, як запустити повторно (`python main.py --calibrate`), що дає «Пропустити».

- [ ] **Step 4: Запустити тести**

Run: `python -m pytest tests -q`
Expected: усі PASS

- [ ] **Step 5: Закомітити**

```bash
git add main.py README.md QUICKSTART.md tests/test_main_setup.py
git commit -m "$(cat <<'EOF'
Run the calibration wizard on first start

Calibration is checked right after the credentials: a stale one is rescaled
to the current window silently, a missing one opens the wizard, and skipping
it is a supported outcome that leaves match accepting working. --calibrate
reopens the wizard at any time.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Діагностичний пакет

**Files:**
- Create: `diagnostics.py`
- Modify: `main.py` (прапорець `--diagnose`)
- Test: `tests/test_diagnostics.py`

**Interfaces:**
- Consumes: `dota_window`, `Calibration`, `DotaHelper.locate`, `config.APP_VERSION`
- Produces: `collect_report(window, calibration) -> dict`, `build_bundle(out_dir, window, calibration, frame) -> Path`

Токен бота і вміст `.env` не потрапляють в архів за жодних умов.

- [ ] **Step 1: Написати тест, що падає**

```python
# tests/test_diagnostics.py
# -*- coding: utf-8 -*-
"""Діагностичний архів: корисний для розбору, безпечний для відправки."""
import json
import zipfile

import pytest
from PIL import Image

import calibration as cal
import diagnostics
import mock_dota
from dota_window import RelRect, WindowInfo

WINDOW = WindowInfo(-254, -1440, 1920, 1080, "Dota 2")
SECRET = "123456789:AAsecret-token-value-that-must-never-leak"


@pytest.fixture
def store(tmp_path):
    store = cal.Calibration.load(tmp_path / "calibration")
    store.window_size = (1920, 1080)
    store.add("search_btn", Image.new("RGB", (330, 50), (58, 110, 48)),
              RelRect(0.74, 0.82, 0.17, 0.046), "manual")
    store.save()
    return store


def test_report_describes_the_setup(store):
    report = diagnostics.collect_report(WINDOW, store)

    assert report["window"] == {"left": -254, "top": -1440,
                                "width": 1920, "height": 1080}
    assert report["calibration"]["window"] == [1920, 1080]
    assert report["calibration"]["elements"]["search_btn"]["source"] == "manual"
    assert "accept" not in report["calibration"]["elements"]
    assert report["app_version"]


def test_report_without_dota_running(store):
    report = diagnostics.collect_report(None, store)

    assert report["window"] is None
    assert report["screens"]


def test_bundle_contains_report_and_screenshot(tmp_path, store):
    frame, _ = mock_dota.render_menu()

    bundle = diagnostics.build_bundle(tmp_path / "out", WINDOW, store, frame)

    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        assert "report.json" in names
        assert "screenshot.png" in names
        report = json.loads(archive.read("report.json"))
        assert report["window"]["width"] == 1920


def test_bundle_never_contains_the_token(tmp_path, store, monkeypatch):
    """Регресія на найгірший можливий результат: витік токена в публічний issue."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", SECRET)
    frame, _ = mock_dota.render_menu()

    bundle = diagnostics.build_bundle(tmp_path / "out", WINDOW, store, frame)

    with zipfile.ZipFile(bundle) as archive:
        assert not any(name.endswith(".env") for name in archive.namelist())
        for name in archive.namelist():
            assert SECRET.encode() not in archive.read(name)
```

- [ ] **Step 2: Запустити тест і переконатися, що він падає**

Run: `python -m pytest tests/test_diagnostics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'diagnostics'`

- [ ] **Step 3: Написати збірку пакета**

```python
# diagnostics.py
# -*- coding: utf-8 -*-
"""Діагностичний пакет для розбору поламок у користувачів."""
import ctypes
import json
import platform
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image

from config import APP_VERSION
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

def collect_report(window, calibration) -> dict:
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
    report = collect_report(window, calibration)

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
```

```python
# main.py — обробка прапорця перед звичайним запуском
def run_diagnostics() -> None:
    """Зібрати діагностичний пакет і показати його користувачу."""
    import diagnostics
    from calibration import Calibration

    window = dota_window.find_window()
    frame = dota_window.capture(window) if dota_window.is_usable(window) else None
    store = Calibration.load(config.CALIBRATION_DIR)

    bundle = diagnostics.build_bundle(
        Path(__file__).parent / "diagnostics", window, store, frame
    )

    print(f"\nДіагностичний архів: {bundle}")
    print("У ньому є знімок гри — на ньому видно твій нік у Steam.")
    print("Токен бота в архів не потрапляє. Перевір вміст перед відправкою.")
```

```python
# main.py — у main(), одразу після перевірки конфігурації
    if "--diagnose" in sys.argv:
        run_diagnostics()
        return
```

- [ ] **Step 4: Запустити тести**

Run: `python -m pytest tests -q`
Expected: усі PASS

- [ ] **Step 5: Закомітити**

```bash
git add diagnostics.py main.py tests/test_diagnostics.py
git commit -m "$(cat <<'EOF'
Add a diagnostics bundle

With no second machine to test on, a bundle the user can attach to an issue
is the only way to see why recognition failed on their setup: screens,
window rect, calibration sources and the captured frame. The token and the
.env contents never enter the archive, and the user is told the screenshot
is in there before they send it.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Ручна матриця і фіналізація

**Files:**
- Create: `docs/testing-matrix.md`
- Create: `tests/corpus/README.md`
- Modify: `README.md` (розділ про діагностику)

**Interfaces:**
- Consumes: усе попереднє
- Produces: чек-лист ручної перевірки та корпус реальних знімків

Синтетика доводить алгоритми, а не реальність. Це — єдині справжні дані.

- [ ] **Step 1: Написати чек-лист**

```markdown
<!-- docs/testing-matrix.md -->
# Ручна матриця перевірки

Синтетичні тести доводять математику розпізнавання, але не те, що справжня
Dota виглядає як наші макети. Ці п'ять прогонів — єдине справжнє свідчення.

Перед релізом пройти всі рядки. Кожен знімок з прогону зберегти в
`tests/corpus/` з іменем `<конфігурація>_<елемент>.png`.

| # | Конфігурація | Кроки | Очікування |
|---|---|---|---|
| 1 | 1080p без рамки, RU | `--calibrate`, пройти майстер, дочекатися матчу | усі три елементи знайдено, матч прийнято, `accept.png` з'явився з `source: opportunistic` |
| 2 | той самий клієнт EN | змінити мову в Steam, `--calibrate` | майстер працює з чужим текстом, автопідказка або ручна рамка |
| 3 | 1280×720 у вікні | змінити роздільну здатність, **не** калібрувати | калібрування перераховано автоматично, кнопки знаходяться |
| 4 | масштаб UI на максимум | посунути повзунок у налаштуваннях Dota | або підлаштувалось, або прийшло повідомлення про калібрування |
| 5 | Dota на другому моніторі | перетягнути вікно | вікно знайдено, кнопки знаходяться, `--diagnose` показує правильний прямокутник |

Після кожного прогону: `python main.py --diagnose` і зберегти архів у
`tests/corpus/`.
```

```markdown
<!-- tests/corpus/README.md -->
# Корпус реальних знімків

Знімки справжньої Dota з ручних прогонів (`docs/testing-matrix.md`) і з
діагностичних архівів користувачів. На них ганяються зміни розпізнавання
без повторного запуску гри.

Іменування: `<ширина>x<висота>_<мова>_<елемент>.png`.

Перед додаванням знімка користувача: переконатися, що на ньому немає
особистих даних, які він не готовий публікувати.
```

- [ ] **Step 2: Пройти матрицю**

Виконати всі п'ять рядків. Для кожного зафіксувати результат у `docs/testing-matrix.md` окремою колонкою «пройдено / дата». Знайдені розбіжності порогів `CONFIDENCE_*` записати в `.env.example` як нові значення за замовчуванням.

Це єдиний крок плану, який не можна виконати автоматично — потрібна запущена Dota.

- [ ] **Step 3: Додати корпус у тести**

```python
# tests/test_corpus.py
# -*- coding: utf-8 -*-
"""Розпізнавання на справжніх знімках Dota з ручних прогонів."""
from pathlib import Path

import pytest
from PIL import Image

import image_recognition as ir

CORPUS = Path(__file__).parent / "corpus"
ACCEPT_SHOTS = sorted(CORPUS.glob("*_accept.png"))


@pytest.mark.skipif(not ACCEPT_SHOTS, reason="корпус ще не зібрано")
@pytest.mark.parametrize("shot", ACCEPT_SHOTS, ids=lambda p: p.stem)
def test_accept_button_found_on_real_screenshots(shot):
    with Image.open(shot) as frame:
        assert ir.find_green_button(frame.convert("RGB")) is not None
```

- [ ] **Step 4: Запустити повний набір**

Run: `python -m pytest tests -q`
Expected: усі PASS; тести корпусу пропускаються, доки знімків немає, і вмикаються самі після кроку 2

- [ ] **Step 5: Закомітити**

```bash
git add docs/testing-matrix.md tests/corpus/README.md tests/test_corpus.py README.md
git commit -m "$(cat <<'EOF'
Add the manual verification matrix and screenshot corpus

Synthetic mocks prove the scaling maths, not that real Dota looks like them,
so five manual passes on real configurations are the actual evidence. Their
screenshots become a corpus that later changes are replayed against offline,
which also turns every user diagnostics bundle into a regression test.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**1. Spec coverage**

| Розділ специфікації | Задача |
|---|---|
| 3. `dota_window.py` | 1, 2 |
| 3. `calibration.py` | 4 |
| 3. `calibration_wizard.py` | 8, 9 |
| 3. Зміни в `image_recognition.py` | 3, 6 |
| 3. Зміни в `dota_helper.py`, один знімок за ітерацію | 6 |
| 3. Зміни в `config.py`, `main.py` | 6, 10 |
| 4. Формат калібрування, `version`, `source` | 4 |
| 4. Самокалібрування `accept` | 7 |
| 4. Застарілість і масштабування | 4, 10 |
| 5. Потік майстра, F10, «Пропустити», чорний кадр | 8, 9 |
| 6. `NO_GAME`, деградація, меню Telegram | 6 |
| 6. Діагностика | 11 |
| 7. Шар 1 (модульні) | 1, 2, 4 |
| 7. Шар 2 (синтетика) | 5 |
| 7. Шар 3 (ручна матриця, корпус) | 12 |
| 8. Відкладене (`%LOCALAPPDATA%`, Valve) | поза планом, свідомо |

Прогалин немає.

**2. Placeholder scan**

Перевірено: немає «TBD», «додати обробку помилок», «тести за аналогією». Єдине місце з описом замість коду — текст `_WizardDialog` у Task 9, крок 3: схема кроків задана, але повний Qt-код діалогу пишеться на місці. Це свідомо, бо діалог перевіряється тестами потоку в тому ж кроці 4, і його точний вигляд залежить від того, як ляже верстка.

**3. Type consistency**

- `WindowInfo`, `RelRect` визначені в Task 1-2, використовуються скрізь однаково.
- `Box` — наявний namedtuple з `image_recognition`, не переоголошується.
- `find_template(needle, haystack, confidence, offset)` — одна сигнатура в задачах 3, 5, 6, 8.
- `find_green_button(image, offset, debug_path)` — одна сигнатура в задачах 3, 5, 6, 8.
- `Calibration.has/element/template_path/search_region/scale_to/is_stale/add` — визначені в Task 4, викликаються з тими самими іменами в 6, 7, 9, 10, 11.
- `ELEMENTS = ("search_btn", "searching", "stop", "accept")` — ті самі імена в калібруванні, `CONFIDENCE` і `SHIPPED`. Ключ `CONFIDENCE` перейменовано з `stop_btn` на `stop` у Task 6, щоб збігався з іменем елемента; змінна оточення `CONFIDENCE_STOP_BTN` лишається старою заради сумісності `.env`.
