# -*- coding: utf-8 -*-
"""Автопідказка та перевірки майстра калібрування — чиста логіка, без Qt."""
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


@pytest.mark.parametrize("confidence", [0.7, wiz.AUTO_DETECT_CONFIDENCE],
                         ids=["default", "production"])
def test_no_candidates_on_noisy_menu(tmp_path, confidence):
    """
    Перевіряти треба й на тому порозі, з яким майстер працює насправді:
    AUTO_DETECT_CONFIDENCE = 0.45 значно нижчий за типове значення 0.7.
    """
    small, small_rects = mock_dota.render_menu(1920, 1080)
    x, y, w, h = small_rects["search_btn"]
    template = tmp_path / "search_game.png"
    small.crop((x, y, x + w, y + h)).save(template)

    assert wiz.detect_candidates(mock_dota.render_noisy_menu(), [template],
                                 confidence=confidence) == []


def test_candidates_are_deduplicated(tmp_path):
    """Той самий елемент, знайдений на кількох масштабах, — один кандидат."""
    frame, rects = mock_dota.render_menu(1920, 1080)
    x, y, w, h = rects["search_btn"]
    template = tmp_path / "a.png"
    frame.crop((x, y, x + w, y + h)).save(template)
    second = tmp_path / "b.png"
    frame.crop((x, y, x + w, y + h)).save(second)

    assert len(wiz.detect_candidates(frame, [template, second])) == 1


def test_one_template_matches_at_multiple_scales(tmp_path):
    """Один шаблон на кількох масштабах — один кандидат найкращої якості."""
    frame, rects = mock_dota.render_menu(1920, 1080)
    x, y, w, h = rects["search_btn"]
    template = tmp_path / "search_game.png"
    frame.crop((x, y, x + w, y + h)).save(template)

    # На тому ж кадрі масштаби 0.9-1.1 усі матимуть хороший збіг
    candidates = wiz.detect_candidates(frame, [template], confidence=0.7)

    # Але результат має бути один — найкраще матчування
    assert len(candidates) == 1
    # Результат має бути дуже близько до оригіналу
    assert abs(candidates[0].left - x) <= 2
    assert abs(candidates[0].top - y) <= 2
    assert abs(candidates[0].width - w) <= 2
    assert abs(candidates[0].height - h) <= 2


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
