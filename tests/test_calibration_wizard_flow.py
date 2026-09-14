# -*- coding: utf-8 -*-
"""
Вікно майстра калібрування: CropLabel і потік майстра без показу вікон.

keyboard підміняється фейком у кожному тесті (fake_keyboard) — тести не
повинні чіпати реальні хуки ОС. make_dialog додатково гарантує, що гаряча
клавіша знімається в teardown, навіть якщо тест сам не закрив діалог.
"""
import os
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image

import calibration as cal
import calibration_wizard_dialog as wiz
import image_recognition as ir
import mock_dota
from dota_window import WindowInfo, to_relative
from image_recognition import Box


@pytest.fixture
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fake_keyboard(monkeypatch):
    """Підмінити keyboard — тести не повинні встановлювати реальні хуки ОС."""
    state = {"registered": [], "released": []}

    def add_hotkey(key, callback):
        handle = (key, callback)
        state["registered"].append(handle)
        return handle

    def remove_hotkey(handle):
        state["released"].append(handle)

    fake = types.SimpleNamespace(add_hotkey=add_hotkey, remove_hotkey=remove_hotkey)
    monkeypatch.setattr(wiz, "keyboard", fake)
    return state


@pytest.fixture
def make_dialog(qt_app, fake_keyboard):
    """
    Створити _WizardDialog і гарантовано зняти його гарячу клавішу в
    teardown — незалежно від того, чи тест сам довів діалог до save/skip.
    Жоден тест не повинен лишати клавішу зареєстрованою після себе.
    """
    created = []

    def _make(store):
        dialog = wiz._WizardDialog(store)
        created.append(dialog)
        return dialog

    yield _make

    for dialog in created:
        dialog._release_hotkey()
        assert dialog._hotkey_handle is None


# --- CropLabel ---------------------------------------------------------------

def test_crop_label_maps_selection_back_to_frame(qt_app):
    """Рамка малюється на зменшеному знімку, а координати потрібні справжні."""
    from PyQt6.QtCore import QPoint

    frame, _ = mock_dota.render_menu(1920, 1080)
    label = wiz.CropLabel()
    label.set_frame(frame, display_width=960)

    label.begin_selection(QPoint(100, 200))
    label.update_selection(QPoint(200, 250))
    rect = label.finish_selection(QPoint(200, 250))

    assert rect == (200, 400, 200, 100)


def test_crop_label_rejects_tiny_selection(qt_app):
    from PyQt6.QtCore import QPoint

    frame, _ = mock_dota.render_menu(1920, 1080)
    label = wiz.CropLabel()
    label.set_frame(frame, display_width=960)

    label.begin_selection(QPoint(100, 100))
    assert label.finish_selection(QPoint(102, 101)) is None


# --- Потік майстра -------------------------------------------------------------

def test_wizard_saves_confirmed_candidate(tmp_path, monkeypatch, make_dialog):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    menu, rects = mock_dota.render_menu()
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.dota_window, "capture", lambda w: menu)
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = make_dialog(wiz.Calibration.load(tmp_path / "calibration"))
    dialog.capture_step("search_btn")
    dialog.confirm_candidate()
    dialog.save_and_close()

    element = dialog.store.element("search_btn")
    assert element is not None
    assert element.rect.x == pytest.approx(rects["search_btn"][0] / 1920, abs=0.01)


def test_wizard_warns_on_blank_capture(tmp_path, monkeypatch, make_dialog):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.dota_window, "capture",
                        lambda w: Image.new("RGB", (1920, 1080), (0, 0, 0)))
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = make_dialog(wiz.Calibration.load(tmp_path / "calibration"))
    dialog.capture_step("search_btn")

    assert "оконн" in dialog.status.text().lower() or "рамк" in dialog.status.text().lower()


# --- Item 1: майстер завжди повертається на передній план ----------------------

def test_capture_step_brings_wizard_to_front_on_blank_capture(tmp_path, monkeypatch, make_dialog):
    """Чорний знімок (ексклюзивний повноекранний режим) — найважливіший випадок
    для bring-to-front: користувач у Dota не бачить попередження, поки майстер
    не спливе сам."""
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.dota_window, "capture",
                        lambda w: Image.new("RGB", (1920, 1080), (0, 0, 0)))
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = make_dialog(wiz.Calibration.load(tmp_path / "calibration"))
    calls = []
    monkeypatch.setattr(dialog, "_bring_to_front", lambda: calls.append(True))

    dialog.capture_step("search_btn")

    assert calls, "Майстер має повернутися на передній план навіть після чорного знімка"


def test_capture_step_brings_wizard_to_front_when_window_missing(tmp_path, monkeypatch, make_dialog):
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: None)
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = make_dialog(wiz.Calibration.load(tmp_path / "calibration"))
    calls = []
    monkeypatch.setattr(dialog, "_bring_to_front", lambda: calls.append(True))

    dialog.capture_step("search_btn")

    assert calls, "Майстер має повернутися на передній план, навіть якщо вікно Dota не знайдено"


def test_run_check_brings_wizard_to_front_on_blank_capture(tmp_path, monkeypatch, make_dialog):
    """Той самий bring-to-front застосовується і до 'Перевірити зараз', бо
    capture_step і _run_check тепер діляться одним _capture_fresh_frame."""
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.dota_window, "capture",
                        lambda w: Image.new("RGB", (1920, 1080), (0, 0, 0)))
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = make_dialog(wiz.Calibration.load(tmp_path / "calibration"))
    calls = []
    monkeypatch.setattr(dialog, "_bring_to_front", lambda: calls.append(True))

    dialog._run_check()

    assert calls


# --- Items 2/3: гаряча клавіша підмінена і завжди звільняється -----------------

def test_dialog_registers_and_releases_hotkey_through_fake(tmp_path, monkeypatch,
                                                            fake_keyboard, make_dialog):
    """keyboard підмінено на фейк — жоден реальний хук ОС не встановлюється."""
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = make_dialog(wiz.Calibration.load(tmp_path / "calibration"))
    assert len(fake_keyboard["registered"]) == 1
    assert fake_keyboard["released"] == []

    dialog.save_and_close()

    assert len(fake_keyboard["released"]) == 1


# --- Skip: підтримуваний результат, не помилка ---------------------------------

def test_skip_keeps_already_confirmed_progress(tmp_path, monkeypatch, make_dialog):
    """Пропуск не повинен викидати вже підтверджені елементи, і приймання
    матчів лишається робочим (пошук за кольором) незалежно від калібрування."""
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    menu, rects = mock_dota.render_menu()
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.dota_window, "capture", lambda w: menu)
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)
    monkeypatch.setattr(wiz.QMessageBox, "question",
                        lambda *a, **kw: wiz.QMessageBox.StandardButton.Yes)

    dialog = make_dialog(wiz.Calibration.load(tmp_path / "calibration"))
    dialog.capture_step("search_btn")
    dialog.confirm_candidate()

    dialog._skip()

    assert dialog.saved is True
    assert dialog.store.element("search_btn") is not None


def test_skip_without_any_progress_does_not_claim_saved(tmp_path, monkeypatch, make_dialog):
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: None)
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)
    monkeypatch.setattr(wiz.QMessageBox, "question",
                        lambda *a, **kw: wiz.QMessageBox.StandardButton.Yes)

    dialog = make_dialog(wiz.Calibration.load(tmp_path / "calibration"))
    dialog._skip()

    assert dialog.saved is False


# --- Кілька кандидатів: гравець обирає -----------------------------------------

def test_multiple_candidates_lets_user_pick(tmp_path, monkeypatch, make_dialog):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    menu, rects = mock_dota.render_menu()
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.dota_window, "capture", lambda w: menu)
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    x, y, w, h = rects["search_btn"]
    wrong = Box(10, 10, w, h)
    right = Box(x, y, w, h)
    monkeypatch.setattr(wiz, "detect_candidates", lambda *a, **kw: [wrong, right])

    dialog = make_dialog(wiz.Calibration.load(tmp_path / "calibration"))
    dialog.capture_step("search_btn")

    assert not dialog.candidates_box.isHidden()
    assert dialog._candidates == [wrong, right]

    dialog._select_candidate(1)

    element = dialog.store.element("search_btn")
    assert element is not None
    assert element.rect.x == pytest.approx(x / 1920, abs=0.001)


# --- Крок 5: перевірка робить рівно те, що робитиме бот ------------------------

def _rescaled_store(tmp_path, small, big):
    """
    Калібрування, зняте на `small` і перераховане під `big`.

    1920x1080 → 1366x768 — саме той випадок, заради якого існує
    SCALED_CONFIDENCE: перерахований LANCZOS шаблон збігається на 0.65,
    але вже не збігається на звичайному для search_btn порозі 0.70.
    """
    frame, rects = mock_dota.render_menu(small.width, small.height)
    store = cal.Calibration.load(tmp_path / "calibration")
    store.window_size = (small.width, small.height)
    x, y, w, h = rects["search_btn"]
    store.add("search_btn", frame.crop((x, y, x + w, y + h)),
              to_relative(small, (x, y, w, h)), "manual")
    store.save()
    store.scale_to(big)

    target, _ = mock_dota.render_menu(big.width, big.height)
    return store, target


def test_check_uses_the_same_confidence_as_the_bot(tmp_path, monkeypatch, make_dialog):
    """
    Крок 5 існує, щоб не заявляти про успіх без перевірки того, що
    робитиме бот. Перевірка з іншими порогами зводить свою мету нанівець:
    для елемента з source == "scaled" бот шукає з SCALED_CONFIDENCE, а
    «Перевірити зараз» рапортувало «НЕ знайдено» те, що бот знаходить.
    """
    big = WindowInfo(0, 0, 1366, 768, "Dota 2")
    store, target = _rescaled_store(tmp_path, WindowInfo(0, 0, 1920, 1080, "Dota 2"), big)
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: big)
    monkeypatch.setattr(wiz.dota_window, "capture", lambda w: target)
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = make_dialog(store)
    dialog._run_check()

    # Те саме, що знаходить бот, майстер має показати знайденим
    assert "search_btn: знайдено" in dialog.status.text()
    assert ir.locate_element(store, "search_btn", big, target) is not None
