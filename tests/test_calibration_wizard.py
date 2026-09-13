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
