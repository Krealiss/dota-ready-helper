# -*- coding: utf-8 -*-
"""
Dota Ready Helper v2.0
Автоматичне прийняття матчів у Dota 2 з керуванням через Telegram.
"""
import sys
import pyautogui as pag
import keyboard

from logger import logger
from config import validate_config
from telegram_bot import TelegramBot
from dota_helper import DotaHelper
from error_handler import setup_exception_handler

def setup_hotkeys(helper: DotaHelper):
    """Налаштувати гарячі клавіші."""

    def on_f6():
        helper.toggle_pause()

    def on_f7():
        helper.stop()

    def on_f8():
        helper.pending_start = True
        logger.info("[HOTKEY] Запит на старт пошуку")

    def on_f9():
        helper.pending_stop = True
        logger.info("[HOTKEY] Запит на стоп пошуку")

    keyboard.add_hotkey("F6", on_f6)
    keyboard.add_hotkey("F7", on_f7)
    keyboard.add_hotkey("F8", on_f8)
    keyboard.add_hotkey("F9", on_f9)

    logger.info("Гарячі клавіші налаштовано")

def main():
    """Точка входу."""
    logger.info("=" * 50)
    logger.info("Dota Ready Helper v2.0")
    logger.info("=" * 50)

    # Перевірка конфігурації
    if not validate_config():
        logger.error("❌ Помилка конфігурації. Перевір файл .env")
        logger.info("Створи файл .env на основі .env.example")
        input("\nНатисни Enter для виходу...")
        sys.exit(1)

    logger.info("✅ Конфігурація валідна")

    # Увімкнути failsafe (рух миші в кут екрана зупиняє PyAutoGUI)
    pag.FAILSAFE = True

    # Ініціалізація Telegram бота
    telegram_bot = TelegramBot()

    # Налаштувати обробник помилок
    setup_exception_handler(telegram_bot)

    # Ініціалізація Dota Helper
    helper = DotaHelper(telegram_bot)

    # Прив'язати callback'и
    telegram_bot.on_start_callback = lambda: setattr(helper, 'pending_start', True)
    telegram_bot.on_stop_callback = lambda: setattr(helper, 'pending_stop', True)
    telegram_bot.on_stats_callback = lambda: setattr(helper, 'pending_stats', True)
    telegram_bot.on_export_callback = lambda: setattr(helper, 'pending_export', True)

    # Налаштувати гарячі клавіші
    setup_hotkeys(helper)

    # Запустити Telegram polling
    telegram_bot.start_polling()

    # Запустити основний цикл
    try:
        helper.run()
    except KeyboardInterrupt:
        logger.info("Отримано сигнал переривання")
        helper.stop()
    except Exception as e:
        logger.error(f"Критична помилка: {e}", exc_info=True)
        telegram_bot.send_message(f"❌ Критична помилка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
