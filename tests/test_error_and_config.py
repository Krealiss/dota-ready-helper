# -*- coding: utf-8 -*-
"""Обробка помилок і читання .env не повинні валити програму."""
import importlib

import pytest

import config
from error_handler import ErrorHandler


class FakeBot:
    def __init__(self):
        self.messages = []

    def send_message(self, text):
        self.messages.append(text)


def test_ordinary_error_is_swallowed_and_reported():
    bot = FakeBot()

    with ErrorHandler("Тестова операція", bot, silent=True):
        raise ValueError("щось пішло не так")

    assert len(bot.messages) == 1
    assert "Тестова операція" in bot.messages[0]


def test_keyboard_interrupt_is_not_swallowed():
    """Регресія: Ctrl+C глушився і програма не завершувалась."""
    with pytest.raises(KeyboardInterrupt):
        with ErrorHandler("Тестова операція", FakeBot(), silent=True):
            raise KeyboardInterrupt()


def test_system_exit_is_not_swallowed():
    with pytest.raises(SystemExit):
        with ErrorHandler("Тестова операція", FakeBot(), silent=True):
            raise SystemExit(1)


def test_successful_block_reports_nothing():
    bot = FakeBot()

    with ErrorHandler("Тестова операція", bot, silent=True):
        pass

    assert bot.messages == []


@pytest.mark.parametrize("raw,expected", [
    ("0.55", 0.55),
    ("", 0.80),
    ("   ", 0.80),
    ("не число", 0.80),
    ("0,80", 0.80),          # кома замість крапки
])
def test_env_float_falls_back_to_default(monkeypatch, raw, expected):
    monkeypatch.setenv("CONFIDENCE_ACCEPT", raw)
    assert config._env_float("CONFIDENCE_ACCEPT", 0.80) == expected


def test_env_float_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv("CONFIDENCE_ACCEPT", raising=False)
    assert config._env_float("CONFIDENCE_ACCEPT", 0.80) == 0.80


@pytest.mark.parametrize("raw,expected", [
    ("800", 800),
    ("800.5", 1000),        # дробове значення не є цілим
    ("широкий", 1000),
    ("", 1000),
])
def test_env_int_falls_back_to_default(monkeypatch, raw, expected):
    monkeypatch.setenv("ACCEPT_REGION_WIDTH", raw)
    assert config._env_int("ACCEPT_REGION_WIDTH", 1000) == expected


SHIPPED_PATH_NAMES = ("IMG_SEARCHING", "IMG_SEARCH_BTN", "IMG_ACCEPT", "IMG_STOP")


def test_validate_config_does_not_depend_on_shipped_assets(monkeypatch, tmp_path):
    """
    Готові PNG — лише підказка всередині майстра (спека §3). Відсутній файл
    підказки не має бути приводом не запуститися; для збірки .exe без
    assets/ це взагалі означало б падіння до будь-якого коду, здатного
    пояснити причину.
    """
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "123:AA")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    for name in SHIPPED_PATH_NAMES:
        monkeypatch.setattr(config, name, tmp_path / "missing.png", raising=False)

    assert config.validate_config() is True


def test_shipped_filenames_live_only_in_the_wizard():
    """Ruling 1: calibration_wizard.SHIPPED — єдине джерело цих імен."""
    import calibration_wizard

    for name in SHIPPED_PATH_NAMES:
        assert not hasattr(config, name), f"config.{name} — друга копія імені файла"

    assert calibration_wizard.SHIPPED


def test_config_imports_with_broken_env(monkeypatch):
    """Регресія: некоректне число у .env валило імпорт config до валідації."""
    monkeypatch.setenv("CONFIDENCE_ACCEPT", "дуже впевнено")
    monkeypatch.setenv("SCAN_INTERVAL", "швидко")
    monkeypatch.setenv("NO_GAME_POLL_INTERVAL", "не скоро")

    try:
        reloaded = importlib.reload(config)

        assert reloaded.CONFIDENCE["accept"] == 0.80
        assert reloaded.SCAN_INTERVAL == 0.30
        assert reloaded.NO_GAME_POLL_INTERVAL == 2.0
    finally:
        # повернути модуль до стану з реального оточення
        monkeypatch.undo()
        importlib.reload(config)
