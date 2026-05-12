# -*- coding: utf-8 -*-
"""
Dota Ready Helper v2.1 - GUI версія
Автоматичне прийняття матчів у Dota 2 з GUI та статистикою.
"""
import sys
import threading
import pyautogui as pag
import keyboard
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

from logger import logger
from config import validate_config
from telegram_bot import TelegramBot
from dota_helper import DotaHelper
from gui import DotaHelperGUI
from setup_dialog import SetupDialog

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

def run_helper_thread(helper: DotaHelper):
    """Запустити helper у окремому потоці."""
    try:
        helper.run()
    except Exception as e:
        logger.error(f"Помилка у helper: {e}", exc_info=True)

def main():
    """Точка входу."""
    logger.info("=" * 50)
    logger.info("Dota Ready Helper v2.1 (GUI)")
    logger.info("=" * 50)

    # Увімкнути failsafe
    pag.FAILSAFE = True

    # Запустити GUI
    app = QApplication(sys.argv)
    app.setApplicationName("Dota Ready Helper")
    app.setOrganizationName("DotaHelper")

    # Перевірка конфігурації
    env_file = Path(__file__).parent / ".env"

    if not env_file.exists() or not validate_config():
        logger.warning("Конфігурація відсутня або невалідна")

        # Показати діалог налаштування
        setup_dialog = SetupDialog()
        if setup_dialog.exec() == setup_dialog.DialogCode.Accepted:
            bot_token, chat_id = setup_dialog.get_credentials()

            # Створити .env файл
            try:
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
                    f.write(f"TELEGRAM_CHAT_ID={chat_id}\n")
                logger.info("Конфігурацію збережено")
            except Exception as e:
                logger.error(f"Помилка збереження конфігурації: {e}")
                QMessageBox.critical(
                    None,
                    "Помилка",
                    f"Не вдалось зберегти конфігурацію:\n{e}"
                )
                sys.exit(1)
        else:
            logger.info("Налаштування скасовано користувачем")
            sys.exit(0)

    logger.info("✅ Конфігурація валідна")

    # Ініціалізація Telegram бота
    try:
        telegram_bot = TelegramBot()

        # Перевірка підключення
        logger.info("Перевірка Telegram підключення...")
        telegram_bot.send_message("✅ Dota Ready Helper запущено успішно!")
        logger.info("✅ Telegram підключення працює")

    except Exception as e:
        logger.error(f"Помилка підключення до Telegram: {e}")
        QMessageBox.critical(
            None,
            "Помилка Telegram",
            f"Не вдалось підключитись до Telegram:\n{e}\n\n"
            "Перевірте:\n"
            "1. Bot Token правильний\n"
            "2. Chat ID правильний\n"
            "3. Ви відправили /start боту\n"
            "4. Є інтернет підключення"
        )
        sys.exit(1)

    # Ініціалізація Dota Helper
    helper = DotaHelper(telegram_bot)

    # Прив'язати callback'и
    telegram_bot.on_start_callback = lambda: setattr(helper, 'pending_start', True)
    telegram_bot.on_stop_callback = lambda: setattr(helper, 'pending_stop', True)
    telegram_bot.on_stats_callback = lambda: setattr(helper, 'pending_stats', True)

    # Налаштувати гарячі клавіші
    setup_hotkeys(helper)

    # Запустити Telegram polling
    telegram_bot.start_polling()

    # Запустити helper у окремому потоці
    helper_thread = threading.Thread(target=run_helper_thread, args=(helper,), daemon=True)
    helper_thread.start()

    # Запустити GUI
    app = QApplication(sys.argv)
    app.setApplicationName("Dota Ready Helper")
    app.setOrganizationName("DotaHelper")

    # Показати splash screen
    from splash_screen import show_splash_screen
    splash = show_splash_screen(app, duration=2000)

    # Створити головне вікно
    window = DotaHelperGUI(helper, telegram_bot)

    # Закрити splash та показати вікно
    def show_window():
        splash.close()
        window.show()

    QTimer.singleShot(2000, show_window)

    # Запустити event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
