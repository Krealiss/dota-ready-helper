# -*- coding: utf-8 -*-
"""GUI для Dota Ready Helper з системним треєм."""
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSystemTrayIcon, QMenu,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QGridLayout
)
from PyQt6.QtCore import QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QAction

from logger import logger
from stats_tracker import Statistics

class DotaHelperGUI(QMainWindow):
    """Головне вікно GUI."""

    def __init__(self, helper, telegram_bot):
        super().__init__()
        self.helper = helper
        self.telegram_bot = telegram_bot
        self.stats = helper.stats

        self.init_ui()
        self.init_tray()
        self.init_timers()

    def init_ui(self):
        """Ініціалізувати інтерфейс."""
        self.setWindowTitle("Dota Ready Helper v2.1")
        self.setGeometry(100, 100, 600, 500)

        # Центральний віджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Статус
        status_group = QGroupBox("Статус")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("⏹ Не активний")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        status_layout.addWidget(self.status_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Статистика
        stats_group = QGroupBox("Статистика")
        stats_layout = QGridLayout()

        self.stats_labels = {
            "total": QLabel("Всього прийнято: 0"),
            "today": QLabel("Сьогодні: 0"),
            "avg_time": QLabel("Середній час: 0с"),
            "session": QLabel("У сесії: 0")
        }

        stats_layout.addWidget(self.stats_labels["total"], 0, 0)
        stats_layout.addWidget(self.stats_labels["today"], 0, 1)
        stats_layout.addWidget(self.stats_labels["avg_time"], 1, 0)
        stats_layout.addWidget(self.stats_labels["session"], 1, 1)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Кнопки керування
        controls_group = QGroupBox("Керування")
        controls_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶️ Запустити")
        self.start_btn.clicked.connect(self.on_start)

        self.stop_btn = QPushButton("⏹ Зупинити")
        self.stop_btn.clicked.connect(self.on_stop)
        self.stop_btn.setEnabled(False)

        self.pause_btn = QPushButton("⏸ Пауза")
        self.pause_btn.clicked.connect(self.on_pause)

        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.pause_btn)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        # Лог
        log_group = QGroupBox("Лог")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

    def init_tray(self):
        """Ініціалізувати системний трей."""
        # Завантажити іконку
        icon_path = Path(__file__).parent / "assets" / "icon.ico"
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            self.tray_icon = QSystemTrayIcon(icon, self)
        else:
            self.tray_icon = QSystemTrayIcon(self)

        # Меню трею
        tray_menu = QMenu()

        show_action = QAction("Показати", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        start_action = QAction("▶️ Запустити", self)
        start_action.triggered.connect(self.on_start)
        tray_menu.addAction(start_action)

        stop_action = QAction("⏹ Зупинити", self)
        stop_action.triggered.connect(self.on_stop)
        tray_menu.addAction(stop_action)

        tray_menu.addSeparator()

        stats_action = QAction("📊 Статистика", self)
        stats_action.triggered.connect(self.show_stats)
        tray_menu.addAction(stats_action)

        tray_menu.addSeparator()

        quit_action = QAction("Вихід", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def init_timers(self):
        """Ініціалізувати таймери оновлення."""
        # Оновлення статистики кожні 2 секунди
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)

        # Оновлення статусу кожну секунду
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)

    def update_stats(self):
        """Оновити відображення статистики."""
        summary = self.stats.get_summary()

        self.stats_labels["total"].setText(
            f"Всього прийнято: {summary['total_matches_accepted']}"
        )
        self.stats_labels["today"].setText(
            f"Сьогодні: {summary['today_accepted']}"
        )
        self.stats_labels["avg_time"].setText(
            f"Середній час: {summary['average_wait_time']:.1f}с"
        )
        self.stats_labels["session"].setText(
            f"У сесії: {summary['current_session_matches']}"
        )

    def update_status(self):
        """Оновити відображення статусу."""
        if self.helper.paused:
            self.status_label.setText("⏸ Пауза")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: orange;")
        elif self.helper.state.value == "searching":
            self.status_label.setText("🔎 Пошук активний")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
        elif self.helper.state.value == "ready":
            self.status_label.setText("✅ Матч знайдено!")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: blue;")
        else:
            self.status_label.setText("⏹ Не активний")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")

    def on_start(self):
        """Запустити пошук."""
        self.helper.pending_start = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.add_log("▶️ Запуск пошуку...")

    def on_stop(self):
        """Зупинити пошук."""
        self.helper.pending_stop = True
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_log("⏹ Зупинка пошуку...")

    def on_pause(self):
        """Пауза/продовження."""
        self.helper.toggle_pause()
        if self.helper.paused:
            self.pause_btn.setText("▶️ Продовжити")
            self.add_log("⏸ Пауза")
        else:
            self.pause_btn.setText("⏸ Пауза")
            self.add_log("▶️ Продовження")

    def show_stats(self):
        """Показати детальну статистику."""
        stats_text = self.stats.get_formatted_summary()
        self.add_log(stats_text)

    def add_log(self, message: str):
        """Додати повідомлення у лог."""
        self.log_text.append(message)

    def on_tray_activated(self, reason):
        """Обробка кліку по іконці трею."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def closeEvent(self, event):
        """Обробка закриття вікна."""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Dota Ready Helper",
            "Програма згорнута у трей",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def quit_app(self):
        """Вихід з програми."""
        self.helper.stop()
        QApplication.quit()
