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
