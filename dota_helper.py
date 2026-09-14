# -*- coding: utf-8 -*-
"""Основна логіка Dota Ready Helper."""
import time
from enum import Enum
from pathlib import Path

from logger import logger
import config
import dota_window
from calibration import Calibration
from config import (
    SCAN_INTERVAL, MESSAGE_COOLDOWN, CALIBRATION_DIR, NO_GAME_POLL_INTERVAL
)
from image_recognition import (
    locate_element, is_inside_accept_region, click_center, double_click_center
)
from stats_tracker import Statistics
from report_exporter import ReportExporter
from error_handler import ErrorHandler

# Скільки ітерацій поспіль жоден відкалібрований елемент не впізнається,
# перш ніж попередити про зміну інтерфейсу. При SCAN_INTERVAL = 0.3 c це
# близько 12 секунд суцільної невдачі в меню — довше за будь-яку анімацію
# переходу і коротше за терпіння користувача.
INTERFACE_MISS_LIMIT = 40

# Скільки кадрів поспіль без попапа «Прийняти» означає, що матч уже не
# приймається і зі стану READY час виходити. Не один кадр: попап може не
# впізнатися на окремому знімку (анімація появи, курсор поверх кнопки), а
# кожна зміна стану шле нове меню в Telegram.
READY_EXIT_MISSES = 3

# Скільки часу після прийнятого матчу не рахувати невдачі розпізнавання.
# Лічильник не відрізняє «меню перестало збігатися» від «меню немає, бо йде
# гра», а дешевого сигналу про це на екрані немає. Зате точно відомо, коли
# ми натиснули «Прийняти»: 90 хвилин перекривають навіть довгий матч із
# запасом. Ціна — у користувача, в якого інтерфейс зламався саме після
# матчу, повідомлення затримається; запізніле правдиве попередження краще
# за вчасне хибне, яке привчає його ігнорувати.
ACCEPT_SUPPRESSION_SECONDS = 90 * 60

class State(Enum):
    """Стани бота."""
    NO_GAME = "no_game"
    IDLE = "idle"
    SEARCHING = "searching"
    READY = "ready"

class DotaHelper:
    """Основний клас для моніторингу та автоматизації Dota 2."""

    def __init__(self, telegram_bot, calibration=None):
        self.telegram_bot = telegram_bot
        self.running = True
        self.paused = False
        self.state = State.NO_GAME
        self.last_message_time = {}

        # Тригери з Telegram
        self.pending_start = False
        self.pending_stop = False
        self.pending_stats = False
        self.pending_export = False

        self.calibration = calibration or Calibration.load(CALIBRATION_DIR)

        # Облік стійкої невдачі розпізнавання (спека §4)
        self._miss_streak = 0
        self._interface_warned = False
        self._seen_element = False

        # Кадрів поспіль без попапа «Прийняти»
        self._accept_misses = 0

        # Коли востаннє прийняли матч (0 — ще жодного в цій сесії)
        self._last_accept_time = 0.0

        # Статистика
        self.stats = Statistics()
        self.exporter = ReportExporter(self.stats)

    def _debounced_message(self, text: str):
        """Надіслати повідомлення з антиспамом."""
        now = time.time()
        last = self.last_message_time.get(text, 0)

        if now - last >= MESSAGE_COOLDOWN:
            self.telegram_bot.send_message(text)
            self.last_message_time[text] = now

    def _set_state(self, new_state: State):
        """Змінити стан та оновити меню."""
        if self.state != new_state:
            logger.info(f"Стан: {self.state.value} → {new_state.value}")
            self.state = new_state
            self.telegram_bot.send_menu(new_state.value)

    def locate(self, name, window, frame):
        """
        Знайти елемент у вже знятому кадрі вікна.

        Для "accept" працює пошук за кольором навіть без калібрування.
        Сама логіка — спільна з діагностикою та майстром.
        """
        return locate_element(self.calibration, name, window, frame)

    def tick(self):
        """Одна ітерація циклу. Повертає паузу до наступної."""
        # Ruling 9: /stats і /export не залежать від вікна Dota, тому
        # обробляються до перевірки вікна — інакше вони мовчки чекають на
        # запуск гри, хоча раніше (у старому run()) працювали завжди.
        if self.pending_stats:
            self.pending_stats = False
            self.telegram_bot.send_message(self.stats.get_formatted_summary())
            return 0.3

        if self.pending_export:
            self.pending_export = False
            self._handle_export()
            return 0.3

        window = dota_window.find_window()
        if not dota_window.is_usable(window):
            self._set_state(State.NO_GAME)
            self._answer_pending_without_game()
            return NO_GAME_POLL_INTERVAL

        if self.state is State.NO_GAME:
            # NO_GAME означає «немає вікна», а не «нічого не впізнано».
            # Вікно є — виходимо зі стану одразу: з порожнім калібруванням
            # жоден елемент не впізнається, і бот лишався б у NO_GAME усю
            # сесію, а меню Telegram — порожнім (спека §6: «калібрування
            # пропущено → приймання працює, на «Запустити пошук» приходить
            # «потрібне калібрування»»).
            self._set_state(State.IDLE)

        self._rescale_if_window_changed(window)

        frame = dota_window.capture(window)

        if self.pending_start:
            self.pending_start = False
            self._handle_start(window, frame)
            return 0.6

        if self.pending_stop:
            self.pending_stop = False
            self._handle_stop(window, frame)
            return 0.6

        if self.check_accept_button(window, frame):
            return 1.0

        if self.locate("searching", window, frame):
            self._note_recognition(True)
            if self.state is not State.SEARCHING:
                self._set_state(State.SEARCHING)
                self._debounced_message("🔎 Пошук гри активний.")
                self.stats.start_search()
            return SCAN_INTERVAL

        search_button = self.locate("search_btn", window, frame)
        self._note_recognition(bool(search_button))
        if search_button:
            self._set_state(State.IDLE)

        return SCAN_INTERVAL

    def run(self):
        """Основний цикл моніторингу."""
        logger.info("🟢 Dota Ready Helper запущено")
        logger.info("Гарячі клавіші: F6 — пауза, F7 — вихід, F8 — старт, F9 — стоп")
        self._debounced_message("🟢 Dota Ready Helper запущено.")
        self.telegram_bot.send_menu(self.state.value)

        while self.running:
            if self.paused:
                time.sleep(0.3)
                continue
            time.sleep(self.tick())

        logger.info("🔴 Dota Ready Helper зупинено")

    def _answer_pending_without_game(self):
        """Пояснити, чому команда не виконується, поки Dota не запущена."""
        if self.pending_start or self.pending_stop:
            self.pending_start = self.pending_stop = False
            self._debounced_message("⚠️ Dota 2 не запущена.")

    def _rescale_if_window_changed(self, window):
        """
        Перерахувати шаблони, якщо вікно тепер іншого розміру.

        Звичайний порядок запуску — спершу помічник, потім Dota, тому на
        старті вікна ще немає і main.ensure_calibrated цю перевірку
        пропускає. Без перевірки в циклі шаблони лишалися б старого розміру
        всю сесію: область пошуку масштабується разом з вікном, а пікселі
        шаблона — ні, і відкалібровані елементи тихо перестають збігатися.

        Ціна — порівняння двох чисел за ітерацію; перерахунок робиться лише
        на зміну.
        """
        if not self.calibration.is_stale(window):
            return

        logger.info("Розмір вікна змінився — перераховую калібрування")
        self.calibration.scale_to(window)

        # Перерахованим шаблонам — чистий старт: попередні невдачі
        # стосувалися шаблонів іншого розміру
        self._miss_streak = 0
        self._interface_warned = False

    def _note_recognition(self, found: bool):
        """
        Порахувати невдачі розпізнавання поспіль і попередити про зміну
        інтерфейсу (спека §4: одне повідомлення, без зупинки роботи).

        Рахуємо тільки те, що справді мало б упізнатися: калібрування є,
        хоч раз уже впізналося в цій сесії, бот вважає, що зараз меню або
        черга, і з моменту прийнятого матчу минуло досить часу, щоб гра
        встигла скінчитися (ruling 13). Під час матчу меню на екрані немає
        зовсім, і рахувати це за поламаний інтерфейс не можна.
        """
        if found:
            self._seen_element = True
            # Щось збіглося — гра явно скінчилася, рахуємо далі як звичайно
            self._last_accept_time = 0.0
            self._miss_streak = 0
            self._interface_warned = False
            return

        if self._interface_warned or not self._seen_element:
            return
        if time.time() - self._last_accept_time < ACCEPT_SUPPRESSION_SECONDS:
            return
        if self.state not in (State.IDLE, State.SEARCHING):
            return
        if not (self.calibration.has("search_btn") or self.calibration.has("searching")):
            return

        self._miss_streak += 1
        if self._miss_streak < INTERFACE_MISS_LIMIT:
            return

        self._interface_warned = True
        logger.warning(
            f"{self._miss_streak} ітерацій поспіль без розпізнавання — "
            "схоже, інтерфейс змінився"
        )
        self._debounced_message(
            "⚠️ Схоже, інтерфейс Dota змінився — знайомі кнопки перестали "
            "збігатися.\nЗапусти калібрування: `python main.py --calibrate`.\n"
            "Приймання матчів тим часом працює."
        )

    def _needs_calibration(self, name) -> bool:
        if self.calibration.has(name):
            return False
        self._debounced_message(
            "⚠️ Потрібне калібрування: запусти `python main.py --calibrate`.\n"
            "Приймання матчів працює й без нього."
        )
        return True

    def _handle_start(self, window, frame):
        if self._needs_calibration("search_btn"):
            return
        button = self.locate("search_btn", window, frame)
        if not button:
            self._debounced_message(
                "⚠️ Не знайшов 'Пошук гри' на екрані.\n"
                "Відкрий головне меню Dota 2."
            )
            return
        double_click_center(button, interval=0.5)
        self._debounced_message("▶️ Пошук гри запущено.")
        self._set_state(State.SEARCHING)
        self.stats.start_search()

    def _handle_stop(self, window, frame):
        if self._needs_calibration("stop"):
            return
        button = self.locate("stop", window, frame)
        if not button:
            self._debounced_message("⚠️ Не знайшов кнопку 'Стоп'.")
            return
        click_center(button)
        self._debounced_message("⏹ Пошук гри зупинено.")
        self._set_state(State.IDLE)

    def _handle_export(self):
        with ErrorHandler("Експорт звітів", self.telegram_bot, silent=True):
            export_dir = Path(__file__).parent / "exports"
            results = self.exporter.export_all(export_dir)
            self.telegram_bot.send_message(
                f"📥 Експорт завершено!\n\nУспішно: {sum(results.values())}/4 форматів"
            )

    def _learn_accept(self, window, frame, box):
        """
        Запам'ятати кнопку 'Прийняти' з першого спійманого матчу.

        Показати цей попап на вимогу неможливо, тому шаблон знімається
        під час реальної гри й далі працює точний збіг.

        Захист у глибину: записуємо лише те, що лежить у центральній
        області вікна. Шаблон пишеться на диск один раз і назавжди —
        помилка детектора тут отруїла б калібрування без шансу
        самовиправитися.
        """
        if self.calibration.has("accept"):
            return

        if not is_inside_accept_region(window, box):
            logger.warning(
                "Кнопку 'Прийняти' знайдено поза центром вікна — "
                "шаблон не зберігаю"
            )
            return

        with ErrorHandler("Самокалібрування 'Прийняти'", silent=True):
            local = (box.left - window.left, box.top - window.top)
            crop = frame.crop((local[0], local[1],
                               local[0] + box.width, local[1] + box.height))

            if not self.calibration.window_size:
                self.calibration.window_size = (window.width, window.height)

            self.calibration.add(
                "accept", crop,
                dota_window.to_relative(window, (box.left, box.top,
                                                 box.width, box.height)),
                "opportunistic"
            )
            self.calibration.save()

    def _save_corpus_frame(self, window, frame):
        """
        Зберегти кадр з вікном прийняття для корпусу реальних знімків.

        Попап живе кілька секунд, і бот натискає кнопку майже одразу, тому
        зняти його вручну неможливо — а це єдиний кадр, який потребує
        tests/test_corpus.py. Кадр у нас уже в руках саме в потрібну мить,
        лишається його не викинути.

        Один файл на розмір вікна: корпусу потрібне покриття конфігурацій, а
        не сотні знімків тієї самої. Зберігається після кліку, у теку, яка
        не потрапляє в git — вирішує людина, що з нього публікувати.
        """
        with ErrorHandler("Збереження кадру для корпусу", silent=True):
            target = (config.CORPUS_DIR
                      / f"{window.width}x{window.height}_accept.png")
            if target.exists():
                return

            target.parent.mkdir(parents=True, exist_ok=True)
            frame.save(target)
            logger.info(f"Кадр для корпусу збережено: {target.name}")

    def _leave_ready_when_popup_is_gone(self):
        """
        Вийти зі стану READY, коли попап «Прийняти» зник з екрана.

        READY означає «матч приймається просто зараз». Вийти з нього можна
        було лише впізнавши search_btn або searching — а в користувача з
        пропущеним калібруванням немає жодного з них, тому стан лишався
        READY до кінця сесії й наступний попап мовчки не натискався:
        приймання працювало рівно один раз за запуск. Вихід зі стану не
        повинен залежати від калібрування, бо саме ця залежність і була
        помилкою.
        """
        if self.state is not State.READY:
            return

        self._accept_misses += 1
        if self._accept_misses >= READY_EXIT_MISSES:
            self._accept_misses = 0
            self._set_state(State.IDLE)

    def check_accept_button(self, window, frame) -> bool:
        """Знайти кнопку 'Прийняти' у кадрі та натиснути її."""
        accept = self.locate("accept", window, frame)
        if not accept:
            self._leave_ready_when_popup_is_gone()
            return False

        # Попап на місці — поки він видно, стан READY лишається, і
        # повторного кліку по тій самій кнопці не буде
        self._accept_misses = 0

        if self.state is not State.READY:
            self._set_state(State.READY)
            self._debounced_message("✅ Гра знайдена! Натискаю 'Прийняти'...")

            if not click_center(accept):
                self.stats.match_missed()
                self._debounced_message(
                    "⚠️ Не вдалося натиснути 'Прийняти'. Прийми матч вручну!"
                )
                return True

            # Далі почнеться матч: на час гри меню на екрані не буде, і
            # лічильник невдач розпізнавання має мовчати (ruling 13)
            self._last_accept_time = time.time()

            self.stats.match_accepted()
            self._learn_accept(window, frame, accept)
            self._save_corpus_frame(window, frame)
            summary = self.stats.get_summary()
            self._debounced_message(
                f"🎮 Гру прийнято!\n\n"
                f"📊 Сьогодні прийнято: {summary['today_accepted']}\n"
                f"📈 Всього: {summary['total_matches_accepted']}"
            )
        return True

    def toggle_pause(self):
        """Перемкнути паузу."""
        self.paused = not self.paused
        msg = "⏸ Пауза" if self.paused else "▶️ Продовжую моніторинг"
        self.telegram_bot.send_message(msg)
        logger.info(msg)

    def stop(self):
        """Зупинити бота."""
        self.running = False
        self.telegram_bot.send_message("🔴 Бот зупинено.")
        logger.info("🔴 Вихід")
