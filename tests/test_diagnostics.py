# -*- coding: utf-8 -*-
"""Діагностичний архів: корисний для розбору, безпечний для відправки."""
import json
import zipfile

import pytest
from PIL import Image

import calibration as cal
import diagnostics
import mock_dota
from dota_window import RelRect, WindowInfo, to_relative

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
    assert "detection" in report


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


def test_bundle_without_screenshot(tmp_path, store):
    """Архів має працювати без знімка (Dota закрита)."""
    bundle = diagnostics.build_bundle(tmp_path / "out", WINDOW, store, frame=None)

    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        assert "report.json" in names
        assert "screenshot.png" not in names
        report = json.loads(archive.read("report.json"))
        assert report["window"]["width"] == 1920


def test_no_stray_files_in_bundle(tmp_path, store):
    """Архів містить лише відкалібровані елементи, не випадкові файли."""
    frame, _ = mock_dota.render_menu()

    # Додати випадковий файл у директорію калібрування
    stray = store.directory / "notes.txt"
    stray.write_text("Це не повинно потрапити в архів")

    bundle = diagnostics.build_bundle(tmp_path / "out", WINDOW, store, frame)

    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        # Переконатися, що файл search_btn є
        assert any("search_btn" in name for name in names)
        # Переконатися, що notes.txt нема
        assert not any("notes.txt" in name for name in names)


def test_detect_elements_with_no_window(store):
    """Без вікна результат невідомий для кожного елемента."""
    detection = diagnostics.detect_elements(None, None, store)

    for name in store.elements.keys():
        assert detection[name] is None


@pytest.fixture
def mixed_store(tmp_path):
    """
    Калібрування, що зачіпає всі гілки пошуку.

    search_btn — source "manual" (звичайний поріг), stop — та сама кнопка
    під іншим ім'ям з source "scaled" (знижений поріг), accept навмисно
    відсутній: його шукає пошук за кольором, і саме таке калібрування має
    кожен, хто ще не спіймав жодного матчу.
    """
    frame, rects = mock_dota.render_menu()
    store = cal.Calibration.load(tmp_path / "calibration")
    store.window_size = (1920, 1080)

    x, y, w, h = rects["search_btn"]
    crop = frame.crop((x, y, x + w, y + h))
    rel = to_relative(WINDOW, (WINDOW.left + x, WINDOW.top + y, w, h))
    store.add("search_btn", crop, rel, "manual")
    store.add("stop", crop, rel, "scaled")
    store.save()
    return store


def test_detection_covers_uncalibrated_elements(mixed_store):
    """
    Баг-репорти пишуть саме ті, хто ще не спіймав матчу, — тобто без
    елемента accept у калібруванні. Найкорисніший рядок пакета мовчки
    пропускав його рівно для них.
    """
    frame, _ = mock_dota.render_ready_popup()

    detection = diagnostics.detect_elements(WINDOW, frame, mixed_store)

    assert set(detection) == set(cal.ELEMENTS)
    assert detection["accept"] is True
    assert detection["searching"] is False       # не відкалібровано і не видно


@pytest.mark.parametrize("render,accept_visible", [
    (mock_dota.render_menu, False),
    (mock_dota.render_ready_popup, True),
])
def test_detect_elements_matches_dota_helper_locate(mixed_store, make_helper,
                                                    render, accept_visible):
    """Виявлення у діагностиці збігається з логікою DotaHelper.locate()."""
    frame, _ = render()
    helper = make_helper(mixed_store)

    detection = diagnostics.detect_elements(WINDOW, frame, mixed_store)

    assert set(detection) == set(cal.ELEMENTS)
    for name in cal.ELEMENTS:
        located = helper.locate(name, WINDOW, frame)
        assert detection[name] is bool(located), (
            f"{name}: locate={located!r}, detect={detection[name]!r}"
        )

    assert detection["accept"] is accept_visible
