from types import SimpleNamespace

import pytest
from PIL import Image

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
