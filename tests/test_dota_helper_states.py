# -*- coding: utf-8 -*-
"""Поведінка циклу залежно від наявності вікна Dota і калібрування."""
import pytest

import calibration as cal
import dota_helper as dh
import image_recognition as ir
import mock_dota
from dota_window import WindowInfo, to_relative

# Ті самі конфігурації, що й у test_recognition_scaling
CONFIGS = [(1920, 1080), (2560, 1440), (1366, 768), (3440, 1440)]


class FakeBot:
    def __init__(self):
        self.messages = []
        self.menus = []

    def send_message(self, text):
        self.messages.append(text)

    def send_menu(self, state):
        self.menus.append(state)


@pytest.fixture
def helper(tmp_path, monkeypatch):
    monkeypatch.setattr(dh, "Statistics", lambda *a, **kw: _FakeStats())
    store = cal.Calibration.load(tmp_path / "calibration")
    return dh.DotaHelper(FakeBot(), calibration=store)


class _FakeStats:
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


def test_no_window_switches_to_no_game(helper, monkeypatch):
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: None)

    helper.tick()

    assert helper.state is dh.State.NO_GAME


def test_minimized_window_is_treated_as_no_game(helper, monkeypatch):
    minimized = WindowInfo(-32000, -32000, 1920, 1080, "Dota 2")
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: minimized)

    helper.tick()

    assert helper.state is dh.State.NO_GAME


def test_start_search_without_calibration_explains_itself(helper, monkeypatch):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, _ = mock_dota.render_menu()
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)
    helper.pending_start = True

    helper.tick()

    assert any("калібрув" in m.lower() for m in helper.telegram_bot.messages)


def test_accept_is_found_without_any_calibration(helper, monkeypatch):
    """Приймання матчу працює навіть коли калібрування пропущено."""
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, rects = mock_dota.render_ready_popup()
    clicked = []
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)
    monkeypatch.setattr(dh, "click_center", lambda box, **kw: clicked.append(box) or True)

    helper.tick()

    assert helper.state is dh.State.READY
    assert clicked and abs(clicked[0].left - rects["accept"][0]) <= 4


def test_single_capture_per_tick(helper, monkeypatch):
    """Знімок вікна робиться один раз, а не окремо для кожної перевірки."""
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, _ = mock_dota.render_menu()
    captures = []
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture",
                        lambda w: captures.append(w) or frame)
    # tick() має право клікнути — клік не повинен дійти до справжньої миші
    monkeypatch.setattr(dh, "click_center", lambda box, **kw: True)

    helper.tick()

    assert len(captures) == 1


def test_pending_stats_answered_without_game_window(helper, monkeypatch):
    """
    Ruling 9: /stats не потребує вікна Dota і не повинен чекати на нього.
    """
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: None)
    monkeypatch.setattr(helper.stats, "get_formatted_summary", lambda: "STATS_TEXT")
    helper.pending_stats = True

    helper.tick()

    assert "STATS_TEXT" in helper.telegram_bot.messages
    assert helper.pending_stats is False


def test_pending_export_runs_without_game_window(helper, monkeypatch):
    """
    Ruling 9: /export теж не потребує вікна Dota — не повинен мовчати,
    доки гра не запущена.
    """
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: None)
    calls = []

    class FakeExporter:
        def export_all(self, output_dir):
            calls.append(output_dir)
            return {"csv": True, "json": True, "html": True, "txt": True}

    helper.exporter = FakeExporter()
    helper.pending_export = True

    helper.tick()

    assert calls, "export_all мав бути викликаний"
    assert helper.pending_export is False
    assert any("Експорт завершено" in m for m in helper.telegram_bot.messages)


def test_scaled_element_is_searched_with_lower_confidence(helper, monkeypatch):
    """
    Ruling 8: елемент з source == "scaled" (перерахований під інший розмір
    вікна) шукається з cal.SCALED_CONFIDENCE замість CONFIDENCE.get(name).

    Поріг вибирає locate_element в image_recognition — єдина реалізація на
    бота, діагностику й майстер, — тому підміняється find_template саме там.
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, rects = mock_dota.render_menu()
    x, y, w, h = rects["search_btn"]

    helper.calibration.directory.mkdir(parents=True, exist_ok=True)
    template = frame.crop((x, y, x + w, y + h))
    helper.calibration.add(
        "search_btn", template, to_relative(window, (x, y, w, h)), "scaled"
    )
    # add() позначає source як переданий аргумент ("scaled"), рівно те, що треба

    captured = {}

    def fake_find_template(needle, haystack, confidence=None, offset=(0, 0)):
        captured["confidence"] = confidence
        return None

    monkeypatch.setattr(ir, "find_template", fake_find_template)

    helper.locate("search_btn", window, frame)

    assert captured["confidence"] == cal.SCALED_CONFIDENCE


def test_accept_is_learned_from_the_first_match(helper, monkeypatch):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, rects = mock_dota.render_ready_popup()
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)
    monkeypatch.setattr(dh, "click_center", lambda box, **kw: True)

    helper.tick()

    element = helper.calibration.element("accept")
    assert element is not None
    assert element.source == "opportunistic"
    assert helper.calibration.template_path("accept").exists()
    assert element.rect.x == pytest.approx(rects["accept"][0] / 1920, abs=0.01)


# --- Кнопка "Почати пошук" — не кнопка "Прийняти" ------------------------------

@pytest.mark.parametrize("language", ["ru", "en", "uk"])
def test_find_match_button_is_not_taken_for_accept(helper, language):
    """
    Детектор кольору не відрізняє «ПОШУК ГРИ» від «ПРИЙНЯТИ»: обидві —
    суцільні зелені прямокутники з білим написом. Розрізняє їх область
    пошуку, бо вікно прийняття завжди в центрі, а кнопка пошуку — внизу
    праворуч.
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, rects = mock_dota.render_menu(1920, 1080, language)

    # Сам детектор кольору кнопку пошуку бачить...
    loose = ir.find_green_button(frame, offset=(window.left, window.top))
    assert loose is not None
    assert abs(loose.left - rects["search_btn"][0]) <= 4

    # ...але як "Прийняти" вона не повинна прийматися
    assert helper.locate("accept", window, frame) is None


def test_main_menu_tick_neither_clicks_nor_learns_accept(helper, monkeypatch):
    """
    Повний tick() на головному меню без калібрування: жодного кліку і
    жодного запису шаблона accept. Інакше бот запускає пошук гри, якого
    користувач не просив, і назавжди отруює свій шаблон «Прийняти».
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, _ = mock_dota.render_menu()
    clicked = []
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)
    monkeypatch.setattr(dh, "click_center",
                        lambda box, **kw: clicked.append(box) or True)

    helper.tick()

    assert clicked == []
    assert helper.calibration.element("accept") is None
    assert helper.state is not dh.State.READY


@pytest.mark.parametrize("width,height", CONFIGS)
def test_ready_popup_is_still_clicked_on_every_config(helper, monkeypatch,
                                                      width, height):
    """Обмеження області не повинно втратити справжнє вікно прийняття."""
    window = WindowInfo(0, 0, width, height, "Dota 2")
    frame, rects = mock_dota.render_ready_popup(width, height)
    clicked = []
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)
    monkeypatch.setattr(dh, "click_center",
                        lambda box, **kw: clicked.append(box) or True)

    helper.tick()

    assert helper.state is dh.State.READY
    assert clicked and abs(clicked[0].left - rects["accept"][0]) <= 4


def test_accept_outside_the_central_region_is_never_learned(helper, monkeypatch):
    """
    Захист у глибину: навіть якщо детектор колись поверне кнопку з краю
    вікна, вона не потрапить у калібрування назавжди.
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, _ = mock_dota.render_menu()
    stray = ir.Box(1421, 886, 331, 51)

    helper._learn_accept(window, frame, stray)

    assert helper.calibration.element("accept") is None
    assert not helper.calibration.template_path("accept").exists()


def test_accept_is_not_relearned_when_already_calibrated(helper, monkeypatch):
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, rects = mock_dota.render_ready_popup()
    x, y, w, h = rects["accept"]
    helper.calibration.window_size = (1920, 1080)
    helper.calibration.add("accept", frame.crop((x, y, x + w, y + h)),
                           to_relative(window, (x, y, w, h)), "manual")
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)
    monkeypatch.setattr(dh, "click_center", lambda box, **kw: True)

    helper.tick()

    assert helper.calibration.element("accept").source == "manual"
