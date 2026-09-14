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
                           confidence=cal.SCALED_CONFIDENCE, offset=region[:2])

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
