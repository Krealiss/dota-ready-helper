# -*- coding: utf-8 -*-
"""Спільні налаштування тестів."""
import sys
from pathlib import Path

import pytest

# Модулі проєкту лежать у корені репозиторію
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyautogui as pag


@pytest.fixture(autouse=True)
def no_real_input(monkeypatch):
    """
    Заглушити ввід pyautogui на час кожного тесту.

    Тест, який забув підмінити click_center, інакше рухає мишу розробника
    і клікає по його робочому столу — причому мовчки, бо перевіряє щось
    інше й однаково проходить. Заглушка ставиться автоматично для всього
    набору, а не в кожному тесті окремо: забути її неможливо.

    Повертає список викликів [(ім'я, args, kwargs)] — тест може перевірити,
    що саме мало б відбутися з мишею.
    """
    calls = []
    monkeypatch.setattr(pag, "moveTo",
                        lambda *args, **kwargs: calls.append(("moveTo", args, kwargs)))
    monkeypatch.setattr(pag, "click",
                        lambda *args, **kwargs: calls.append(("click", args, kwargs)))
    return calls


class FakeBot:
    """Telegram-бот без Telegram: справжній конструює TeleBot з .env."""

    def __init__(self):
        self.messages = []
        self.menus = []

    def send_message(self, text):
        self.messages.append(text)

    def send_menu(self, state):
        self.menus.append(state)


class FakeStats:
    """Статистика без диска: справжня пише в робочу теку stats/ репозиторію."""

    def __init__(self):
        self.accepted = 0

    def start_search(self):
        pass

    def match_accepted(self):
        self.accepted += 1

    def match_missed(self):
        pass

    def get_summary(self):
        return {"today_accepted": 0, "total_matches_accepted": 0}

    def get_formatted_summary(self):
        return ""


@pytest.fixture
def make_helper(monkeypatch):
    """
    Створити DotaHelper на фейкових боті та статистиці.

    Жоден тест не повинен ані ходити в Telegram, ані писати в справжню
    теку stats/ — зокрема тести діагностики, які раніше конструювали
    і TelegramBot, і Statistics по-справжньому.
    """
    import dota_helper as dh

    monkeypatch.setattr(dh, "Statistics", lambda *args, **kwargs: FakeStats())

    def _make(calibration):
        return dh.DotaHelper(FakeBot(), calibration=calibration)

    return _make
