# -*- coding: utf-8 -*-
"""Потік майстра без показу вікон: підміняємо знімок і підтвердження."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

import calibration_wizard as wiz
import mock_dota
from dota_window import WindowInfo


@pytest.fixture
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_wizard_saves_confirmed_candidate(qt_app, tmp_path, monkeypatch):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    menu, rects = mock_dota.render_menu()
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.dota_window, "capture", lambda w: menu)
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = wiz._WizardDialog(wiz.Calibration.load(tmp_path / "calibration"))
    dialog.capture_step("search_btn")
    dialog.confirm_candidate()
    dialog.save_and_close()

    element = dialog.store.element("search_btn")
    assert element is not None
    assert element.rect.x == pytest.approx(rects["search_btn"][0] / 1920, abs=0.01)


def test_wizard_warns_on_blank_capture(qt_app, tmp_path, monkeypatch):
    from PIL import Image

    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    monkeypatch.setattr(wiz.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(wiz.dota_window, "capture",
                        lambda w: Image.new("RGB", (1920, 1080), (0, 0, 0)))
    monkeypatch.setattr(wiz.QDialog, "exec", lambda self: 0)

    dialog = wiz._WizardDialog(wiz.Calibration.load(tmp_path / "calibration"))
    dialog.capture_step("search_btn")

    assert "оконн" in dialog.status.text().lower() or "рамк" in dialog.status.text().lower()
