# -*- coding: utf-8 -*-
"""Спільні налаштування тестів."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Модулі проєкту лежать у корені репозиторію
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Логи тестів — у tmp, і виставити це треба до першого імпорту logger:
# інакше трейсбеки з тестів обробки помилок і фейкові події лягають у
# logs/dota_helper_<дата>.log поруч зі справжніми і псують діагностику
os.environ.setdefault(
    "DOTA_HELPER_LOG_DIR",
    tempfile.mkdtemp(prefix="dota_helper_test_logs_")
)

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


@pytest.fixture(autouse=True)
def corpus_dir(tmp_path, monkeypatch):
    """
    Відвести теку корпусу в tmp на час кожного тесту.

    Бот зберігає кадр з вікном прийняття у config.CORPUS_DIR, і будь-який
    тест, що доганяє tick() до прийняття матчу, писав би туди синтетичний
    макет. Це гірше за просто сміття в репозиторії: файл називається так
    само, як справжній кадр користувача, лягає в ту саму теку — і через
    перевірку «файл уже є» справжній кадр потім не зберігається взагалі.

    Повертає шлях, щоб тест міг перевірити, що саме записано.
    """
    import config

    target = tmp_path / "corpus"
    monkeypatch.setattr(config, "CORPUS_DIR", target)
    return target


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
