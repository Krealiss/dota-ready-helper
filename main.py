# -*- coding: utf-8 -*-
"""
Dota Ready Helper
Автоматичне прийняття матчів у Dota 2 з керуванням через Telegram.
"""
import importlib
import sys
from pathlib import Path
import pyautogui as pag
import keyboard

import config
import dota_window
from calibration import Calibration
from logger import logger
from config import APP_VERSION

def setup_hotkeys(helper):
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

def ensure_configured(force_setup: bool = False) -> bool:
    """
    Перевірити налаштування, за потреби показавши майстер.

    Returns:
        True якщо конфігурація валідна
    """
    if not force_setup and config.validate_config():
        return True

    # Майстер вміє полагодити лише відсутні дані Telegram
    if not force_setup and config.credentials_present():
        return False

    logger.info("Запускаю майстер налаштування")
    from setup_dialog import run_setup

    if not run_setup():
        logger.info("Налаштування скасовано")
        return False

    # Перечитати .env після збереження
    config.load_dotenv(override=True)
    importlib.reload(config)
    return config.validate_config()

def ensure_calibrated(force_setup: bool = False) -> Calibration:
    """
    Переконатися, що калібрування придатне, за потреби показавши майстер.

    Returns:
        Калібрування — можливо порожнє, якщо майстер пропущено
    """
    store = Calibration.load(config.CALIBRATION_DIR)
    window = dota_window.find_window()

    if not force_setup and not store.is_empty():
        if window and store.is_stale(window):
            logger.info("Розмір вікна змінився — перераховую калібрування")
            store.scale_to(window)
        return store

    # Qt-залежний код завантажується лише тут, щоб не тягнути його при
    # старті для користувачів, які майстра ніколи не побачать
    from calibration_wizard_dialog import run_wizard

    if not run_wizard(config.CALIBRATION_DIR):
        logger.info(
            "Калібрування пропущено: приймання матчів працює, "
            "керування пошуком з Telegram — ні"
        )

    return Calibration.load(config.CALIBRATION_DIR)

def run_diagnostics() -> None:
    """Зібрати діагностичний пакет і показати його користувачу."""
    import diagnostics

    window = dota_window.find_window()
    frame = dota_window.capture(window) if dota_window.is_usable(window) else None
    store = Calibration.load(config.CALIBRATION_DIR)

    bundle = diagnostics.build_bundle(
        Path(__file__).parent / "diagnostics", window, store, frame
    )

    print(f"\nДіагностичний архів: {bundle}")
    print("У ньому є знімок гри — на ньому видно твій нік у Steam.")
    print("Токен бота в архів не потрапляє. Перевір вміст перед відправкою.")

def main():
    """Точка входу."""
    logger.info("=" * 50)
    logger.info(f"Dota Ready Helper v{APP_VERSION}")
    logger.info("=" * 50)

    # Перевірка конфігурації (--setup відкриває майстер примусово)
    if not ensure_configured(force_setup="--setup" in sys.argv):
        logger.error("❌ Конфігурація неповна — деталі вище")
        input("\nНатисни Enter для виходу...")
        sys.exit(1)

    logger.info("✅ Конфігурація валідна")

    # Перевірка діагностичного прапорця
    if "--diagnose" in sys.argv:
        run_diagnostics()
        return

    # Перевірка калібрування (--calibrate відкриває майстер примусово)
    calibration = ensure_calibrated(force_setup="--calibrate" in sys.argv)

    # Імпорт після налаштування: ці модулі читають значення з config при імпорті
    from telegram_bot import TelegramBot
    from dota_helper import DotaHelper
    from error_handler import setup_exception_handler

    # Увімкнути failsafe (рух миші в кут екрана зупиняє PyAutoGUI)
    pag.FAILSAFE = True

    # Ініціалізація Telegram бота
    telegram_bot = TelegramBot()

    # Налаштувати обробник помилок
    setup_exception_handler(telegram_bot)

    # Ініціалізація Dota Helper
    helper = DotaHelper(telegram_bot, calibration=calibration)

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
