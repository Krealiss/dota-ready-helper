# -*- coding: utf-8 -*-
"""Стикування майстра налаштування із запуском програми."""
import pytest

import main
import setup_dialog


@pytest.fixture
def wizard(monkeypatch):
    """Підмінити майстер і перезавантаження config, щоб нічого не чіпати."""
    state = {"shown": 0, "result": True, "reloaded": 0}

    def fake_setup():
        state["shown"] += 1
        return state["result"]

    monkeypatch.setattr(setup_dialog, "run_setup", fake_setup)
    monkeypatch.setattr(main.config, "load_dotenv", lambda **kw: None)
    monkeypatch.setattr(main.importlib, "reload",
                        lambda module: state.__setitem__("reloaded",
                                                         state["reloaded"] + 1))
    return state


def set_config(monkeypatch, valid, credentials=True):
    """Задати поведінку перевірок config."""
    results = iter(valid) if isinstance(valid, list) else None
    monkeypatch.setattr(main.config, "validate_config",
                        (lambda: next(results)) if results else (lambda: valid))
    monkeypatch.setattr(main.config, "credentials_present", lambda: credentials)


def test_configured_app_does_not_show_wizard(monkeypatch, wizard):
    set_config(monkeypatch, valid=True)

    assert main.ensure_configured() is True
    assert wizard["shown"] == 0


def test_wizard_runs_when_env_is_missing(monkeypatch, wizard):
    """Перший запуск: даних немає — має відкритися вікно налаштування."""
    set_config(monkeypatch, valid=[False, True], credentials=False)

    assert main.ensure_configured() is True
    assert wizard["shown"] == 1
    assert wizard["reloaded"] == 1      # .env перечитано після збереження


def test_cancelled_wizard_stops_startup(monkeypatch, wizard):
    set_config(monkeypatch, valid=False, credentials=False)
    wizard["result"] = False

    assert main.ensure_configured() is False
    assert wizard["shown"] == 1


def test_saved_but_still_invalid_config_fails(monkeypatch, wizard):
    set_config(monkeypatch, valid=[False, False], credentials=False)

    assert main.ensure_configured() is False
    assert wizard["shown"] == 1


def test_setup_flag_opens_wizard_even_when_configured(monkeypatch, wizard):
    """--setup дозволяє змінити токен чи chat ID будь-коли."""
    set_config(monkeypatch, valid=[True])

    assert main.ensure_configured(force_setup=True) is True
    assert wizard["shown"] == 1


def test_wizard_not_shown_for_problems_it_cannot_fix(monkeypatch, wizard):
    """Дані Telegram на місці, але бракує зображень — майстер тут не допоможе."""
    set_config(monkeypatch, valid=False, credentials=True)

    assert main.ensure_configured() is False
    assert wizard["shown"] == 0
