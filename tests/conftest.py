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
