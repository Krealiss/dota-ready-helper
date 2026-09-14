# -*- coding: utf-8 -*-
"""Основна логіка Dota Ready Helper."""
import time
from enum import Enum
from pathlib import Path

from logger import logger
import dota_window
from calibration import Calibration, SCALED_CONFIDENCE
from config import (
    CONFIDENCE, SCAN_INTERVAL, MESSAGE_COOLDOWN,
    CALIBRATION_DIR, NO_GAME_POLL_INTERVAL, ACCEPT_COLOR_FALLBACK
)
from image_recognition import (
    find_template, find_accept_by_colour, is_inside_accept_region,
    click_center, double_click_center
)
from stats_tracker import Statistics
from report_exporter import ReportExporter
from error_handler import ErrorHandler

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
        """
        if self.calibration.has(name):
            region = self.calibration.search_region(name, window)
            crop = frame.crop((
                region[0] - window.left, region[1] - window.top,
                region[0] - window.left + region[2],
                region[1] - window.top + region[3],
            ))
            element = self.calibration.element(name)
            confidence = (
                SCALED_CONFIDENCE if element.source == "scaled"
                else CONFIDENCE.get(name, 0.8)
            )
            box = find_template(
                self.calibration.template_path(name), crop,
                confidence=confidence, offset=region[:2]
            )
            if box:
                return box

        if name == "accept" and ACCEPT_COLOR_FALLBACK:
            return find_accept_by_colour(window, frame)

        return None

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
            if self.state is not State.SEARCHING:
                self._set_state(State.SEARCHING)
                self._debounced_message("🔎 Пошук гри активний.")
                self.stats.start_search()
            return SCAN_INTERVAL

        if self.locate("search_btn", window, frame):
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

    def check_accept_button(self, window, frame) -> bool:
        """Знайти кнопку 'Прийняти' у кадрі та натиснути її."""
        accept = self.locate("accept", window, frame)
        if not accept:
            return False

        if self.state is not State.READY:
            self._set_state(State.READY)
            self._debounced_message("✅ Гра знайдена! Натискаю 'Прийняти'...")

            if not click_center(accept):
                self.stats.match_missed()
                self._debounced_message(
                    "⚠️ Не вдалося натиснути 'Прийняти'. Прийми матч вручну!"
                )
                return True

            self.stats.match_accepted()
            self._learn_accept(window, frame, accept)
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
