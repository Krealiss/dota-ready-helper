# -*- coding: utf-8 -*-
"""Пошук кнопки 'Прийняти' у різних варіантах вікна прийняття матчу."""
import pytest
from PIL import Image, ImageDraw, ImageFont

import pyautogui as pag
import image_recognition as ir

SCREEN = (1920, 1080)
REGION = (460, 240, 1000, 600)  # get_center_region(1000, 600) для 1920x1080


def _font(size, bold=True):
    for name in ("arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _panel(draw):
    """Рамка вікна прийняття — кнопка лежить усередині неї."""
    draw.rectangle([640, 240, 1280, 800], fill=(30, 33, 36),
                   outline=(96, 168, 96), width=3)


def _label(draw, box, text="ПРИНЯТЬ", size=30):
    x0, y0, x1, y1 = box
    draw.text(((x0 + x1) // 2, (y0 + y1) // 2), text, font=_font(size),
              fill=(255, 255, 255), anchor="mm")


def new_dialog():
    """Вікно 'ВАША ИГРА ГОТОВА / ALL PICK' з деталями якості матчу."""
    img = Image.new("RGB", SCREEN, (26, 28, 30))
    d = ImageDraw.Draw(img)
    _panel(d)
    d.text((960, 300), "ВАША ИГРА ГОТОВА", font=_font(22), fill=(200, 205, 210), anchor="mm")
    d.text((960, 335), "ALL PICK", font=_font(34), fill=(240, 242, 245), anchor="mm")

    button = (700, 380, 1220, 445)
    d.rectangle(button, fill=(62, 123, 54))
    _label(d, button)

    # коричнева панель якості гри та сіра кнопка "ИСКАТЬ ЗАНОВО"
    d.rectangle([690, 480, 1230, 660], fill=(58, 48, 38), outline=(120, 100, 70), width=2)
    d.text((960, 540), "Баланс мастерства: идеальный", font=_font(15, False),
           fill=(150, 200, 150), anchor="mm")
    d.rectangle([1060, 690, 1220, 725], fill=(70, 72, 74))
    return img, (700, 380, 520, 65)


def gradient_dialog():
    """Та сама кнопка, але з градієнтом і світлою окантовкою."""
    img = Image.new("RGB", SCREEN, (26, 28, 30))
    d = ImageDraw.Draw(img)
    _panel(d)

    x0, y0, x1, y1 = 700, 380, 1220, 445
    for i in range(y1 - y0):
        k = i / (y1 - y0)
        d.line([(x0, y0 + i), (x1, y0 + i)],
               fill=(int(78 - 26 * k), int(140 - 34 * k), int(66 - 20 * k)))
    d.rectangle([x0, y0, x1, y1], outline=(150, 200, 140), width=2)
    _label(d, (x0, y0, x1, y1))
    return img, (700, 380, 520, 65)


def old_dialog():
    """Старе вікно з темною кнопкою — як в assets/prinyat.png."""
    img = Image.new("RGB", SCREEN, (26, 28, 30))
    d = ImageDraw.Draw(img)
    button = (800, 500, 1115, 558)
    d.rectangle(button, fill=(45, 74, 62))
    _label(d, button, size=26)
    return img, (800, 500, 315, 58)


def game_screen():
    """Гра без вікна прийняття: зелена міні-мапа, смужки здоров'я, зелений текст."""
    img = Image.new("RGB", SCREEN, (26, 28, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 810, 270, 1080], fill=(34, 70, 40))
    for i in range(12):
        d.rectangle([400 + i * 90, 300, 470 + i * 90, 308], fill=(60, 160, 60))
    d.rectangle([700, 200, 1220, 700], outline=(96, 168, 96), width=3)
    d.text((960, 400), "Поиск игры...", font=_font(28), fill=(120, 200, 120), anchor="mm")
    return img, None


@pytest.fixture
def screen(monkeypatch):
    """Підмінити скриншот екрана заданим зображенням."""

    def _install(img):
        monkeypatch.setattr(
            pag, "screenshot",
            lambda region=None: img.crop((
                region[0], region[1], region[0] + region[2], region[1] + region[3]
            )) if region else img
        )

    return _install


@pytest.mark.parametrize("builder", [new_dialog, gradient_dialog, old_dialog],
                         ids=["all_pick", "gradient", "old"])
def test_green_button_found(screen, builder):
    img, expected = builder()
    screen(img)

    box = ir.find_green_button(REGION)

    assert box is not None, "кнопку 'Прийняти' не знайдено"
    x, y, w, h = expected
    assert abs(box.left - x) <= 4 and abs(box.top - y) <= 4
    assert abs(box.width - w) <= 8 and abs(box.height - h) <= 8


@pytest.mark.parametrize("builder", [new_dialog, gradient_dialog, old_dialog],
                         ids=["all_pick", "gradient", "old"])
def test_click_lands_on_button(screen, builder):
    img, expected = builder()
    screen(img)

    box = ir.find_green_button(REGION)
    point = pag.center(box)

    x, y, w, h = expected
    assert abs(point.x - (x + w // 2)) <= 2
    assert abs(point.y - (y + h // 2)) <= 2


def test_no_false_positive_on_game_screen(screen):
    img, _ = game_screen()
    screen(img)

    assert ir.find_green_button(REGION) is None


def test_button_inside_green_frame_is_not_skipped(screen):
    """Регресія: RETR_EXTERNAL пропускав кнопку всередині рамки вікна."""
    img, expected = new_dialog()
    screen(img)

    box = ir.find_green_button(REGION)

    assert box is not None
    assert box.width == pytest.approx(expected[2], abs=8)


def test_center_region_is_clamped_to_screen():
    """Завеликий регіон не повинен виходити за межі екрана."""
    sw, sh = pag.size()
    left, top, width, height = ir.get_center_region(sw * 2, sh * 2)

    assert left >= 0 and top >= 0
    assert width <= sw and height <= sh
