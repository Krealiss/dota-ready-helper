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
