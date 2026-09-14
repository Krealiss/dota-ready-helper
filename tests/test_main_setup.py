# -*- coding: utf-8 -*-
"""Стикування майстра налаштування із запуском програми."""
import pytest

import calibration as cal
import calibration_wizard_dialog as wiz
import main
import setup_dialog
from dota_window import WindowInfo


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


@pytest.fixture
def wizard_calls(monkeypatch, tmp_path):
    """Підмінити майстер калібрування, що живе у calibration_wizard_dialog."""
    state = {"shown": 0, "result": True, "dir": tmp_path / "calibration"}

    def fake_wizard(calibration_dir=None):
        state["shown"] += 1
        return state["result"]

    monkeypatch.setattr(wiz, "run_wizard", fake_wizard)
    monkeypatch.setattr(main.config, "CALIBRATION_DIR", state["dir"])
    return state


def test_calibrated_user_does_not_see_the_wizard(wizard_calls, monkeypatch):
    store = cal.Calibration.load(wizard_calls["dir"])
    store.window_size = (1920, 1080)
    store.elements["search_btn"] = cal.Element("search_btn.png",
                                               cal.RelRect(0.1, 0.1, 0.1, 0.1),
                                               "manual", "2026-01-01T00:00:00")
    store.save()
    (wizard_calls["dir"] / "search_btn.png").write_bytes(b"")

    monkeypatch.setattr(main.dota_window, "find_window",
                        lambda: WindowInfo(0, 0, 1920, 1080, "Dota 2"))

    main.ensure_calibrated()

    assert wizard_calls["shown"] == 0


def test_wizard_runs_when_calibration_missing(wizard_calls, monkeypatch):
    monkeypatch.setattr(main.dota_window, "find_window", lambda: None)

    main.ensure_calibrated()

    assert wizard_calls["shown"] == 1


def test_skipped_calibration_does_not_block_startup(wizard_calls, monkeypatch):
    """Пропуск майстра лишає приймання матчів робочим."""
    wizard_calls["result"] = False
    monkeypatch.setattr(main.dota_window, "find_window", lambda: None)

    store = main.ensure_calibrated()

    assert store is not None
    assert store.is_empty() is True


def test_resolution_change_rescales_calibration(wizard_calls, monkeypatch):
    from PIL import Image

    store = cal.Calibration.load(wizard_calls["dir"])
    store.window_size = (1920, 1080)
    store.add("search_btn", Image.new("RGB", (330, 50), (58, 110, 48)),
              cal.RelRect(0.74, 0.82, 0.17, 0.046), "manual")
    store.save()

    monkeypatch.setattr(main.dota_window, "find_window",
                        lambda: WindowInfo(0, 0, 2560, 1440, "Dota 2"))

    result = main.ensure_calibrated()

    assert result.window_size == (2560, 1440)
    assert wizard_calls["shown"] == 0
