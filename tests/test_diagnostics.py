# -*- coding: utf-8 -*-
"""Діагностичний архів: корисний для розбору, безпечний для відправки."""
import json
import zipfile

import pytest
from PIL import Image

import calibration as cal
import diagnostics
import mock_dota
from dota_window import RelRect, WindowInfo

WINDOW = WindowInfo(-254, -1440, 1920, 1080, "Dota 2")
SECRET = "123456789:AAsecret-token-value-that-must-never-leak"


@pytest.fixture
def store(tmp_path):
    store = cal.Calibration.load(tmp_path / "calibration")
    store.window_size = (1920, 1080)
    store.add("search_btn", Image.new("RGB", (330, 50), (58, 110, 48)),
              RelRect(0.74, 0.82, 0.17, 0.046), "manual")
    store.save()
    return store


def test_report_describes_the_setup(store):
    report = diagnostics.collect_report(WINDOW, store)

    assert report["window"] == {"left": -254, "top": -1440,
                                "width": 1920, "height": 1080}
    assert report["calibration"]["window"] == [1920, 1080]
    assert report["calibration"]["elements"]["search_btn"]["source"] == "manual"
    assert "accept" not in report["calibration"]["elements"]
    assert report["app_version"]


def test_report_without_dota_running(store):
    report = diagnostics.collect_report(None, store)

    assert report["window"] is None
    assert report["screens"]


def test_bundle_contains_report_and_screenshot(tmp_path, store):
    frame, _ = mock_dota.render_menu()

    bundle = diagnostics.build_bundle(tmp_path / "out", WINDOW, store, frame)

    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        assert "report.json" in names
        assert "screenshot.png" in names
        report = json.loads(archive.read("report.json"))
        assert report["window"]["width"] == 1920


def test_bundle_never_contains_the_token(tmp_path, store, monkeypatch):
    """Регресія на найгірший можливий результат: витік токена в публічний issue."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", SECRET)
    frame, _ = mock_dota.render_menu()

    bundle = diagnostics.build_bundle(tmp_path / "out", WINDOW, store, frame)

    with zipfile.ZipFile(bundle) as archive:
        assert not any(name.endswith(".env") for name in archive.namelist())
        for name in archive.namelist():
            assert SECRET.encode() not in archive.read(name)
