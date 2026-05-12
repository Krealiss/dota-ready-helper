# -*- coding: utf-8 -*-
"""Діалог налаштування Telegram для першого запуску."""
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class SetupDialog(QDialog):
    """Діалог налаштування Telegram токенів."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bot_token = ""
        self.chat_id = ""
        self.init_ui()

    def init_ui(self):
        """Ініціалізувати інтерфейс."""
        self.setWindowTitle("Налаштування Dota Ready Helper")
        self.setMinimumWidth(500)
        self.setModal(True)

        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Налаштування Telegram")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Опис
        desc = QLabel(
            "Для роботи програми потрібен Telegram бот.\n"
            "Натисніть 'Інструкція' щоб дізнатись як отримати токени."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(20)

        # Bot Token
        layout.addWidget(QLabel("Bot Token:"))
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        layout.addWidget(self.token_input)

        layout.addSpacing(10)

        # Chat ID
        layout.addWidget(QLabel("Chat ID:"))
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("123456789")
        layout.addWidget(self.chat_input)

        layout.addSpacing(20)

        # Кнопки
        buttons_layout = QHBoxLayout()

        help_btn = QPushButton("📖 Інструкція")
        help_btn.clicked.connect(self.show_instructions)
        buttons_layout.addWidget(help_btn)

        buttons_layout.addStretch()

        cancel_btn = QPushButton("Скасувати")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("✅ Зберегти")
        save_btn.clicked.connect(self.save_config)
        save_btn.setDefault(True)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def show_instructions(self):
        """Показати інструкцію."""
        instructions = """
<h3>Як отримати Telegram токени:</h3>

<h4>1. Створити бота (Bot Token):</h4>
<ol>
<li>Відкрий Telegram і знайди <b>@BotFather</b></li>
<li>Відправ команду <b>/newbot</b></li>
<li>Введи ім'я бота (наприклад: "My Dota Helper")</li>
<li>Введи username бота (має закінчуватись на "bot", наприклад: "my_dota_helper_bot")</li>
<li>BotFather дасть тобі <b>токен</b> - скопіюй його</li>
</ol>

<h4>2. Отримати Chat ID:</h4>
<ol>
<li>Знайди свого бота в Telegram</li>
<li>Натисни <b>Start</b> або відправ будь-яке повідомлення</li>
<li>Відкрий у браузері:<br>
<code>https://api.telegram.org/bot<b>ТУТ_ТВІЙ_ТОКЕН</b>/getUpdates</code></li>
<li>Знайди <b>"chat":{"id":123456789}</b> - це твій Chat ID</li>
</ol>

<h4>Приклад:</h4>
<b>Bot Token:</b> 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz<br>
<b>Chat ID:</b> 123456789
"""

        msg = QMessageBox(self)
        msg.setWindowTitle("Інструкція")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(instructions)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def save_config(self):
        """Зберегти конфігурацію."""
        token = self.token_input.text().strip()
        chat_id = self.chat_input.text().strip()

        # Валідація
        if not token:
            QMessageBox.warning(self, "Помилка", "Введіть Bot Token!")
            return

        if not chat_id:
            QMessageBox.warning(self, "Помилка", "Введіть Chat ID!")
            return

        # Базова перевірка формату
        if ":" not in token:
            QMessageBox.warning(
                self,
                "Помилка",
                "Bot Token має містити ':'\nПриклад: 1234567890:ABCdefGHI..."
            )
            return

        if not chat_id.lstrip('-').isdigit():
            QMessageBox.warning(
                self,
                "Помилка",
                "Chat ID має бути числом\nПриклад: 123456789"
            )
            return

        self.bot_token = token
        self.chat_id = chat_id
        self.accept()

    def get_credentials(self):
        """Отримати введені дані."""
        return self.bot_token, self.chat_id
