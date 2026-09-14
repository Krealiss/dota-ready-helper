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


@pytest.fixture
def helper(tmp_path, make_helper):
    """Бот і статистика — фейкові (conftest), калібрування — порожнє."""
    return make_helper(cal.Calibration.load(tmp_path / "calibration"))


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


# --- Поведінка під час роботи: вікно з'явилось, змінилось, перестало збігатися --

def _calibrate_search_btn(helper, window, frame, rects):
    """Зняти search_btn з макета так само, як це зробив би майстер."""
    x, y, w, h = rects["search_btn"]
    helper.calibration.window_size = (window.width, window.height)
    helper.calibration.add("search_btn", frame.crop((x, y, x + w, y + h)),
                           to_relative(window, (x, y, w, h)), "manual")
    return helper.calibration


def test_window_alone_leaves_no_game(helper, monkeypatch):
    """
    NO_GAME означає «немає вікна». З порожнім калібруванням жоден елемент
    не впізнається, тому стан лишався NO_GAME усю сесію, меню Telegram
    приходило порожнім і кнопки «Запустити пошук» користувач не бачив
    ніколи — разом з поясненням, що потрібне калібрування.
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame, _ = mock_dota.render_menu()
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)

    helper.tick()

    assert helper.state is dh.State.IDLE
    assert "idle" in helper.telegram_bot.menus


def test_window_of_another_size_is_rescaled_at_runtime(helper, monkeypatch):
    """
    Звичайний порядок запуску — спершу помічник, потім Dota, тому на старті
    вікна немає і main.ensure_calibrated перевірку пропускає. Якщо Dota
    відкриється іншого розміру, перерахувати шаблони має цикл.
    """
    small = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    big = WindowInfo(0, 0, 2560, 1440, "Dota 2")
    menu, rects = mock_dota.render_menu(1920, 1080)
    _calibrate_search_btn(helper, small, menu, rects)

    target, _ = mock_dota.render_menu(2560, 1440)
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: big)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: target)

    helper.tick()

    assert helper.calibration.window_size == (2560, 1440)
    assert helper.calibration.element("search_btn").source == "scaled"
    assert helper.locate("search_btn", big, target) is not None


def test_persistent_mismatch_warns_once_and_keeps_working(helper, monkeypatch):
    """
    Спека §4: стійка невдача — одне повідомлення «схоже, інтерфейс
    змінився», без зупинки роботи.
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    menu, rects = mock_dota.render_menu()
    _calibrate_search_btn(helper, window, menu, rects)
    frames = {"current": menu}
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frames["current"])

    helper.tick()                                   # елемент упізнано
    frames["current"] = mock_dota.render_noisy_menu()
    for _ in range(dh.INTERFACE_MISS_LIMIT + 5):
        helper.telegram_bot.messages.clear()        # обійти антиспам за текстом
        helper.last_message_time.clear()
        helper.tick()
        if helper.telegram_bot.messages:
            break

    assert any("інтерфейс" in m for m in helper.telegram_bot.messages)

    # Далі — тиша, поки щось знову не збігається
    helper.telegram_bot.messages.clear()
    helper.last_message_time.clear()
    for _ in range(dh.INTERFACE_MISS_LIMIT + 5):
        helper.tick()

    assert not any("інтерфейс" in m for m in helper.telegram_bot.messages)
    assert helper.running is True


def test_no_interface_warning_without_calibration(helper, monkeypatch):
    """Калібрування пропущено — не впізнається нічого, і це нормально."""
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    frame = mock_dota.render_noisy_menu()
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frame)

    for _ in range(dh.INTERFACE_MISS_LIMIT + 5):
        helper.last_message_time.clear()
        helper.tick()

    assert not any("інтерфейс" in m for m in helper.telegram_bot.messages)


def test_no_interface_warning_during_a_match(helper, monkeypatch):
    """
    Під час матчу жодного елемента меню на екрані немає — це не поламаний
    інтерфейс, і попередження «схоже, інтерфейс змінився» тут хибне.

    Ruling 13: лічильник мовчить не тому, що стан READY (стан правильно
    залишається разом зі зникненням попапа), а тому, що з моменту
    прийнятого матчу минуло менше ACCEPT_SUPPRESSION_SECONDS.
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    menu, rects = mock_dota.render_menu()
    _calibrate_search_btn(helper, window, menu, rects)
    popup, _ = mock_dota.render_ready_popup()
    frames = {"current": menu}
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frames["current"])
    monkeypatch.setattr(dh, "click_center", lambda box, **kw: True)

    helper.tick()                                   # меню: елемент упізнано
    frames["current"] = popup
    helper.tick()                                   # матч знайдено → READY
    assert helper.state is dh.State.READY

    frames["current"] = mock_dota.render_noisy_menu()
    for _ in range(dh.INTERFACE_MISS_LIMIT + 5):
        helper.last_message_time.clear()
        helper.tick()

    assert not any("інтерфейс" in m for m in helper.telegram_bot.messages)


# --- READY означає «зараз приймається матч», а не «матч колись був» -------------

def test_two_matches_are_accepted_in_one_session_without_calibration(helper, monkeypatch):
    """
    Спека §6: з пропущеним калібруванням приймання працює — тобто щоразу,
    а не один раз за запуск. Після першого матчу стан лишався READY, бо
    вийти з нього могло лише впізнавання search_btn чи searching, яких у
    такого користувача немає; другий попап натрапляв на перевірку
    `state is not READY` і не натискався.
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    popup, _ = mock_dota.render_ready_popup()
    menu, _ = mock_dota.render_menu()
    frames = {"current": popup}
    clicked = []
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frames["current"])
    monkeypatch.setattr(dh, "click_center",
                        lambda box, **kw: clicked.append(box) or True)

    helper.tick()                                   # перший матч
    assert len(clicked) == 1

    frames["current"] = menu                        # попап зник
    for _ in range(dh.READY_EXIT_MISSES):
        helper.tick()
    assert helper.state is not dh.State.READY

    frames["current"] = popup                       # другий матч
    helper.tick()

    assert len(clicked) == 2


def test_one_popup_on_screen_is_clicked_exactly_once(helper, monkeypatch):
    """
    Попап висить близько 15 секунд, тобто десятки ітерацій. Клік має бути
    один: вихід зі стану READY не повинен перетворитися на повторні кліки
    по тій самій кнопці.
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    popup, _ = mock_dota.render_ready_popup()
    clicked = []
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: popup)
    monkeypatch.setattr(dh, "click_center",
                        lambda box, **kw: clicked.append(box) or True)

    for _ in range(dh.READY_EXIT_MISSES + 5):
        helper.tick()

    assert len(clicked) == 1
    assert helper.state is dh.State.READY


def test_leaving_ready_does_not_spam_the_telegram_menu(helper, monkeypatch):
    """
    _set_state шле нове меню на кожну зміну, тому стан не має блимати
    між READY та IDLE через один невпізнаний кадр.
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    popup, _ = mock_dota.render_ready_popup()
    menu, _ = mock_dota.render_menu()
    frames = {"current": popup}
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frames["current"])
    monkeypatch.setattr(dh, "click_center", lambda box, **kw: True)

    helper.tick()
    frames["current"] = menu
    helper.tick()                                   # один пропущений кадр

    assert helper.state is dh.State.READY
    assert helper.telegram_bot.menus.count("ready") == 1


def test_interface_warning_returns_after_the_suppression_window(helper, monkeypatch):
    """
    Ruling 13 не повинен глушити попередження назавжди: щойно вікно
    тиші після матчу минуло, стійка невдача знову доповідається.

    Годинник підкручується через записану мітку часу прийнятого матчу —
    чекати 90 хвилин у тесті ніхто не буде.
    """
    window = WindowInfo(0, 0, 1920, 1080, "Dota 2")
    menu, rects = mock_dota.render_menu()
    _calibrate_search_btn(helper, window, menu, rects)
    popup, _ = mock_dota.render_ready_popup()
    frames = {"current": menu}
    monkeypatch.setattr(dh.dota_window, "find_window", lambda: window)
    monkeypatch.setattr(dh.dota_window, "capture", lambda w: frames["current"])
    monkeypatch.setattr(dh, "click_center", lambda box, **kw: True)

    helper.tick()                                   # меню: елемент упізнано
    frames["current"] = popup
    helper.tick()                                   # матч прийнято
    assert helper._last_accept_time > 0

    frames["current"] = mock_dota.render_noisy_menu()
    for _ in range(dh.INTERFACE_MISS_LIMIT + 5):
        helper.last_message_time.clear()
        helper.tick()
    assert not any("інтерфейс" in m for m in helper.telegram_bot.messages)

    # Матч давно скінчився, а меню так і не збігається
    helper._last_accept_time -= dh.ACCEPT_SUPPRESSION_SECONDS + 1
    for _ in range(dh.INTERFACE_MISS_LIMIT + 5):
        helper.last_message_time.clear()
        helper.tick()

    assert any("інтерфейс" in m for m in helper.telegram_bot.messages)
