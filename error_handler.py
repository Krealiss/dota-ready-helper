# -*- coding: utf-8 -*-
"""Система обробки помилок та crash reporter."""
import sys
import traceback
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from logger import logger

class CrashReporter:
    """Клас для збору та відправки звітів про помилки."""

    def __init__(self, app_version: str = "2.1"):
        self.app_version = app_version
        self.crash_dir = Path(__file__).parent / "crashes"
        self.crash_dir.mkdir(exist_ok=True)

    def collect_system_info(self) -> dict:
        """Зібрати інформацію про систему."""
        return {
            "app_version": self.app_version,
            "python_version": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "timestamp": datetime.now().isoformat()
        }

    def save_crash_report(self, exc_type, exc_value, exc_traceback) -> Path:
        """
        Зберегти звіт про помилку.

        Args:
            exc_type: Тип виключення
            exc_value: Значення виключення
            exc_traceback: Traceback

        Returns:
            Шлях до збереженого звіту
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        crash_file = self.crash_dir / f"crash_{timestamp}.json"

        # Форматувати traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)

        # Зібрати дані
        crash_data = {
            "system_info": self.collect_system_info(),
            "error": {
                "type": exc_type.__name__,
                "message": str(exc_value),
                "traceback": tb_text
            }
        }

        # Зберегти
        try:
            with open(crash_file, 'w', encoding='utf-8') as f:
                json.dump(crash_data, f, indent=2, ensure_ascii=False)

            logger.error(f"Crash report saved: {crash_file}")
            return crash_file

        except Exception as e:
            logger.error(f"Failed to save crash report: {e}")
            return None

    def show_error_dialog(self, error_message: str, details: Optional[str] = None):
        """
        Показати діалог з помилкою користувачу.

        Args:
            error_message: Основне повідомлення
            details: Детальна інформація (опціонально)
        """
        try:
            from PyQt6.QtWidgets import QMessageBox, QApplication
            import sys

            # Створити QApplication якщо потрібно
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Помилка - Dota Ready Helper")
            msg.setText(error_message)

            if details:
                msg.setDetailedText(details)

            msg.setStandardButtons(
                QMessageBox.StandardButton.Ok |
                QMessageBox.StandardButton.Close
            )

            msg.exec()

        except Exception as e:
            # Якщо GUI не доступний, виведемо у консоль
            logger.error(f"Error dialog failed: {e}")
            print(f"\n{'='*60}")
            print(f"ERROR: {error_message}")
            if details:
                print(f"\nDetails:\n{details}")
            print(f"{'='*60}\n")

def setup_exception_handler(telegram_bot=None):
    """
    Налаштувати глобальний обробник виключень.

    Args:
        telegram_bot: Екземпляр Telegram бота для відправки сповіщень
    """
    crash_reporter = CrashReporter()

    def exception_handler(exc_type, exc_value, exc_traceback):
        """Обробник необроблених виключень."""
        # Ігнорувати KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Логувати помилку
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

        # Зберегти crash report
        crash_file = crash_reporter.save_crash_report(
            exc_type, exc_value, exc_traceback
        )

        # Відправити у Telegram (якщо доступно)
        if telegram_bot:
            try:
                error_msg = (
                    f"❌ Критична помилка!\n\n"
                    f"Тип: {exc_type.__name__}\n"
                    f"Повідомлення: {str(exc_value)}\n\n"
                    f"Звіт збережено: {crash_file.name if crash_file else 'N/A'}"
                )
                telegram_bot.send_message(error_msg)
            except Exception as e:
                logger.error(f"Failed to send error to Telegram: {e}")

        # Показати діалог користувачу
        error_message = (
            f"Виникла критична помилка:\n\n"
            f"{exc_type.__name__}: {str(exc_value)}\n\n"
            f"Програма буде закрита."
        )

        tb_text = ''.join(traceback.format_exception(
            exc_type, exc_value, exc_traceback
        ))

        crash_reporter.show_error_dialog(error_message, tb_text)

        # Викликати стандартний обробник
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    # Встановити обробник
    sys.excepthook = exception_handler
    logger.info("Exception handler installed")

class ErrorHandler:
    """Контекстний менеджер для обробки помилок."""

    def __init__(self, operation_name: str, telegram_bot=None, silent: bool = False):
        """
        Args:
            operation_name: Назва операції
            telegram_bot: Telegram бот для сповіщень
            silent: Не показувати діалог помилки
        """
        self.operation_name = operation_name
        self.telegram_bot = telegram_bot
        self.silent = silent

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is None:
            return True

        # Логувати помилку
        logger.error(
            f"Error in {self.operation_name}: {exc_value}",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

        # Відправити у Telegram
        if self.telegram_bot:
            try:
                error_msg = (
                    f"⚠️ Помилка у {self.operation_name}\n\n"
                    f"{exc_type.__name__}: {str(exc_value)}"
                )
                self.telegram_bot.send_message(error_msg)
            except Exception:
                pass

        # Показати діалог (якщо не silent)
        if not self.silent:
            crash_reporter = CrashReporter()
            crash_reporter.show_error_dialog(
                f"Помилка у {self.operation_name}",
                str(exc_value)
            )

        # Не пробрасувати виключення далі
        return True

# Приклад використання
if __name__ == "__main__":
    # Тест crash reporter
    reporter = CrashReporter()

    try:
        # Симуляція помилки
        raise ValueError("Test error")
    except Exception:
        exc_info = sys.exc_info()
        crash_file = reporter.save_crash_report(*exc_info)
        print(f"Crash report saved: {crash_file}")
