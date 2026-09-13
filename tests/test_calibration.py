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
    # int() truncates 499.5 to 499
    assert top == 499


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
