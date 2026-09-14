# -*- coding: utf-8 -*-
"""
Запобіжник: жоден тест не має права рухати справжню мишу користувача.

Тест ловиться на тому, що `pyautogui.moveTo`/`pyautogui.click` підмінені
автоматичною фікстурою з conftest. Справжні функції запам'ятовуються на
момент імпорту модуля — тобто до того, як фікстура відпрацювала.
"""
import pyautogui as pag

import image_recognition as ir

_REAL_MOVE_TO = pag.moveTo
_REAL_CLICK = pag.click


def test_pyautogui_is_stubbed_for_every_test():
    """Автофікстура conftest підміняє ввід у кожному тесті, не лише тут."""
    assert pag.moveTo is not _REAL_MOVE_TO
    assert pag.click is not _REAL_CLICK


def test_click_center_never_reaches_the_real_mouse(no_real_input):
    """Навіть прямий виклик click_center лишається всередині заглушки."""
    assert ir.click_center(ir.Box(100, 100, 40, 20)) is True
    assert [name for name, _args, _kwargs in no_real_input] == ["moveTo", "click"]
