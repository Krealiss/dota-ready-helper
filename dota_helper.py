# -*- coding: utf-8 -*-
"""Основна логіка Dota Ready Helper."""
import time
from enum import Enum
from typing import Optional

from logger import logger
from config import (
    IMG_SEARCHING, IMG_SEARCH_BTN, IMG_ACCEPT, IMG_STOP,
    CONFIDENCE, SCAN_INTERVAL, MESSAGE_COOLDOWN, SEARCH_REGION
)
from image_recognition import (
    find_on_screen, click_center, double_click_center, get_center_region
)
from stats_tracker import Statistics
from report_exporter import ReportExporter
from error_handler import ErrorHandler

class State(Enum):
    """Стани бота."""
    IDLE = "idle"
    SEARCHING = "searching"
    READY = "ready"

class DotaHelper:
    """Основний клас для моніторингу та автоматизації Dota 2."""

    def __init__(self, telegram_bot):
        self.telegram_bot = telegram_bot
        self.running = True
        self.paused = False
        self.state = State.IDLE
        self.last_message_time = {}

        # Тригери з Telegram
        self.pending_start = False
        self.pending_stop = False
        self.pending_stats = False
        self.pending_export = False

        # Регіон для пошуку кнопки "Прийняти" (центр екрана)
        self.accept_region = get_center_region(800, 400)

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

    def start_search(self) -> bool:
        """
        Запустити пошук гри через інтерфейс.

        Returns:
            True якщо кнопку знайдено та натиснуто
        """
        search_btn = find_on_screen(
            IMG_SEARCH_BTN,
            confidence=CONFIDENCE["search_btn"],
            region=SEARCH_REGION
        )

        if not search_btn:
            logger.warning("Кнопка 'Пошук гри' не знайдена")
            return False

        double_click_center(search_btn, interval=0.5)
        self._debounced_message("▶️ Пошук гри запущено.")
        self._set_state(State.SEARCHING)
        self.stats.start_search()
        return True

    def stop_search(self) -> bool:
        """
        Зупинити пошук гри через інтерфейс.

        Returns:
            True якщо кнопку знайдено та натиснуто
        """
        stop_btn = find_on_screen(
            IMG_STOP,
            confidence=CONFIDENCE["stop_btn"],
            region=SEARCH_REGION
        )

        if not stop_btn:
            logger.warning("Кнопка 'Стоп' не знайдена")
            return False

        click_center(stop_btn)
        self._debounced_message("⏹ Пошук гри зупинено.")
        self._set_state(State.IDLE)
        return True

    def check_accept_button(self) -> bool:
        """
        Перевірити наявність кнопки "Прийняти" та натиснути її.

        Returns:
            True якщо кнопку знайдено
        """
        accept = find_on_screen(
            IMG_ACCEPT,
            confidence=CONFIDENCE["accept"],
            region=self.accept_region
        )

        if accept:
            if self.state != State.READY:
                self._set_state(State.READY)
                self._debounced_message("✅ Гра знайдена! Натискаю 'Прийняти'...")
                click_center(accept)
                self.stats.match_accepted()

                # Отримати статистику для повідомлення
                summary = self.stats.get_summary()
                msg = (
                    f"🎮 Гру прийнято!\n\n"
                    f"📊 Сьогодні прийнято: {summary['today_accepted']}\n"
                    f"📈 Всього: {summary['total_matches_accepted']}"
                )
                self._debounced_message(msg)
            return True

        return False

    def check_searching_indicator(self) -> bool:
        """
        Перевірити, чи активний пошук гри.

        Returns:
            True якщо індикатор пошуку знайдено
        """
        searching = find_on_screen(
            IMG_SEARCHING,
            confidence=CONFIDENCE["searching"],
            region=SEARCH_REGION
        )

        if searching:
            if self.state != State.SEARCHING:
                self._set_state(State.SEARCHING)
                self._debounced_message("🔎 Пошук гри активний.")
            return True

        return False

    def check_idle_state(self) -> bool:
        """
        Перевірити, чи бот у стані очікування (видно кнопку "Пошук гри").

        Returns:
            True якщо кнопку знайдено
        """
        search_btn = find_on_screen(
            IMG_SEARCH_BTN,
            confidence=CONFIDENCE["search_btn"],
            region=SEARCH_REGION
        )

        if search_btn:
            if self.state != State.IDLE:
                self._set_state(State.IDLE)
            return True

        return False

    def run(self):
        """Основний цикл моніторингу."""
        logger.info("🟢 Dota Ready Helper запущено")
        logger.info("Гарячі клавіші: F6 — пауза, F7 — вихід, F8 — старт, F9 — стоп")

        self._debounced_message("🟢 Dota Ready Helper запущено.")
        self.telegram_bot.send_menu('idle')

        while self.running:
            if self.paused:
                time.sleep(0.3)
                continue

            # Обробка тригерів з Telegram
            if self.pending_start:
                success = self.start_search()
                if not success:
                    self._debounced_message(
                        "⚠️ Не знайшов 'Пошук гри' на екрані.\n"
                        "Відкрий Dota 2 та перейди на головний екран."
                    )
                self.pending_start = False
                time.sleep(0.6)
                continue

            if self.pending_stop:
                success = self.stop_search()
                if not success:
                    self._debounced_message(
                        "⚠️ Не знайшов кнопку 'Стоп'.\n"
                        "Можливо, пошук вже зупинено."
                    )
                self.pending_stop = False
                time.sleep(0.6)
                continue

            # Обробка запиту статистики
            if self.pending_stats:
                stats_text = self.stats.get_formatted_summary()
                self.telegram_bot.send_message(stats_text)
                self.pending_stats = False
                time.sleep(0.3)
                continue

            # Обробка запиту експорту
            if self.pending_export:
                with ErrorHandler("Експорт звітів", self.telegram_bot, silent=True):
                    from pathlib import Path
                    export_dir = Path(__file__).parent / "exports"
                    results = self.exporter.export_all(export_dir)

                    success = sum(results.values())
                    msg = (
                        f"📥 Експорт завершено!\n\n"
                        f"Успішно: {success}/4 форматів\n"
                        f"Папка: {export_dir.name}"
                    )
                    self.telegram_bot.send_message(msg)

                self.pending_export = False
                time.sleep(0.3)
                continue

            # Пріоритет 1: Кнопка "Прийняти"
            if self.check_accept_button():
                time.sleep(1.0)
                continue

            # Пріоритет 2: Індикатор пошуку
            if self.check_searching_indicator():
                time.sleep(SCAN_INTERVAL)
                continue

            # Пріоритет 3: Стан очікування
            self.check_idle_state()
            time.sleep(SCAN_INTERVAL)

        logger.info("🔴 Dota Ready Helper зупинено")

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
