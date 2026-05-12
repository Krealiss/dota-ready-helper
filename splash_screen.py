# -*- coding: utf-8 -*-
"""Splash screen для Dota Ready Helper."""
import sys
import time
from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel, QProgressBar, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont

class SplashScreen(QSplashScreen):
    """Кастомний splash screen з прогрес-баром."""

    def __init__(self):
        # Створити pixmap для splash screen
        pixmap = QPixmap(500, 300)
        pixmap.fill(QColor(30, 30, 40))

        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)

        # Налаштувати стиль
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )

        # Створити віджети
        self.setup_ui()

        # Прогрес
        self.progress = 0

    def setup_ui(self):
        """Налаштувати UI splash screen."""
        # Малювання на pixmap
        pixmap = self.pixmap()
        painter = QPainter(pixmap)

        # Фон
        painter.fillRect(pixmap.rect(), QColor(30, 30, 40))

        # Заголовок
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            pixmap.rect(),
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
            "Dota Ready Helper"
        )

        # Версія
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(
            pixmap.rect().adjusted(0, 60, 0, 0),
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
            "v2.1"
        )

        # Логотип (якщо є)
        # logo = QPixmap("assets/logo.png")
        # painter.drawPixmap(150, 80, 200, 100, logo)

        # Текст "Завантаження..."
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(
            pixmap.rect().adjusted(0, 0, 0, -80),
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
            "Завантаження..."
        )

        # Прогрес-бар (малюємо вручну)
        bar_width = 400
        bar_height = 20
        bar_x = (pixmap.width() - bar_width) // 2
        bar_y = pixmap.height() - 50

        # Фон прогрес-бару
        painter.setPen(QColor(60, 60, 70))
        painter.setBrush(QColor(60, 60, 70))
        painter.drawRoundedRect(bar_x, bar_y, bar_width, bar_height, 10, 10)

        painter.end()
        self.setPixmap(pixmap)

    def update_progress(self, value: int, message: str = ""):
        """Оновити прогрес."""
        self.progress = value

        # Оновити pixmap з новим прогресом
        pixmap = QPixmap(500, 300)
        pixmap.fill(QColor(30, 30, 40))

        painter = QPainter(pixmap)

        # Фон
        painter.fillRect(pixmap.rect(), QColor(30, 30, 40))

        # Заголовок
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            pixmap.rect(),
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
            "Dota Ready Helper"
        )

        # Версія
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(
            pixmap.rect().adjusted(0, 60, 0, 0),
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
            "v2.1"
        )

        # Повідомлення
        if message:
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(
                pixmap.rect().adjusted(0, 0, 0, -80),
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                message
            )

        # Прогрес-бар
        bar_width = 400
        bar_height = 20
        bar_x = (pixmap.width() - bar_width) // 2
        bar_y = pixmap.height() - 50

        # Фон
        painter.setPen(QColor(60, 60, 70))
        painter.setBrush(QColor(60, 60, 70))
        painter.drawRoundedRect(bar_x, bar_y, bar_width, bar_height, 10, 10)

        # Заповнення
        fill_width = int(bar_width * (value / 100))
        painter.setPen(QColor(76, 175, 80))
        painter.setBrush(QColor(76, 175, 80))
        painter.drawRoundedRect(bar_x, bar_y, fill_width, bar_height, 10, 10)

        # Відсоток
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.drawText(
            bar_x, bar_y, bar_width, bar_height,
            Qt.AlignmentFlag.AlignCenter,
            f"{value}%"
        )

        painter.end()
        self.setPixmap(pixmap)

        # Оновити екран
        QApplication.processEvents()

def show_splash_screen(app: QApplication, duration: int = 3000):
    """
    Показати splash screen на вказаний час.

    Args:
        app: QApplication екземпляр
        duration: Тривалість у мілісекундах
    """
    splash = SplashScreen()
    splash.show()

    # Симуляція завантаження
    steps = [
        (20, "Завантаження конфігурації..."),
        (40, "Ініціалізація модулів..."),
        (60, "Підключення до Telegram..."),
        (80, "Завантаження ресурсів..."),
        (100, "Готово!")
    ]

    for progress, message in steps:
        QTimer.singleShot(
            int(duration * progress / 100),
            lambda p=progress, m=message: splash.update_progress(p, m)
        )

    return splash

# Приклад використання
if __name__ == "__main__":
    app = QApplication(sys.argv)

    splash = show_splash_screen(app, duration=3000)

    # Симуляція завантаження
    QTimer.singleShot(3000, splash.close)
    QTimer.singleShot(3000, app.quit)

    sys.exit(app.exec())
