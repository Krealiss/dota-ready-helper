# -*- coding: utf-8 -*-
"""
Майстер початкового налаштування.

Збирає токен Telegram-бота та chat ID, перевіряє їх і записує у .env —
щоб не редагувати файл вручну при першому запуску.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional

import requests

BASE_DIR = Path(__file__).parent.absolute()
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"

API_URL = "https://api.telegram.org/bot{token}/{method}"
REQUEST_TIMEOUT = 10

class SetupError(Exception):
    """Помилка перевірки налаштувань."""

# --- Перевірка формату -----------------------------------------------------

def is_valid_token(token: str) -> bool:
    """Токен від @BotFather має вигляд 123456789:AA...."""
    return bool(re.fullmatch(r"\d{6,12}:[A-Za-z0-9_\-]{30,}", (token or "").strip()))

def is_valid_chat_id(chat_id) -> bool:
    """Chat ID — ціле число, для груп від'ємне."""
    return bool(re.fullmatch(r"-?\d{5,20}", str(chat_id or "").strip()))

# --- Робота з Telegram API -------------------------------------------------

def _call(token: str, method: str, **params) -> dict:
    """Викликати метод Telegram API та повернути result."""
    try:
        response = requests.post(
            API_URL.format(token=token.strip(), method=method),
            data=params,
            timeout=REQUEST_TIMEOUT
        )
    except requests.RequestException as e:
        raise SetupError(f"Немає зв'язку з Telegram: {e}") from e

    try:
        payload = response.json()
    except ValueError as e:
        raise SetupError("Telegram повернув некоректну відповідь") from e

    if not payload.get("ok"):
        raise SetupError(payload.get("description", "Telegram відхилив запит"))

    return payload.get("result")

def parse_chat_id(payload: dict) -> Optional[str]:
    """
    Дістати chat ID з відповіді getUpdates.

    Береться найсвіжіше повідомлення — користувач щойно написав боту.
    """
    updates = (payload or {}).get("result") or []

    for update in reversed(updates):
        for key in ("message", "edited_message", "channel_post", "callback_query"):
            item = update.get(key)
            if key == "callback_query":
                item = (item or {}).get("message")
            chat_id = ((item or {}).get("chat") or {}).get("id")
            if chat_id is not None:
                return str(chat_id)

    return None

def fetch_bot_username(token: str) -> str:
    """Перевірити токен і повернути ім'я бота."""
    result = _call(token, "getMe")
    return result.get("username", "?")

def fetch_chat_id(token: str) -> str:
    """Визначити chat ID за останнім повідомленням боту."""
    try:
        response = requests.get(
            API_URL.format(token=token.strip(), method="getUpdates"),
            timeout=REQUEST_TIMEOUT
        )
        payload = response.json()
    except (requests.RequestException, ValueError) as e:
        raise SetupError(f"Не вдалося отримати оновлення: {e}") from e

    if not payload.get("ok"):
        raise SetupError(payload.get("description", "Telegram відхилив запит"))

    chat_id = parse_chat_id(payload)
    if not chat_id:
        raise SetupError(
            "Повідомлень не знайдено.\n"
            "Напиши боту будь-що у Telegram і натисни кнопку ще раз."
        )

    return chat_id

def send_test_message(token: str, chat_id: str) -> None:
    """Надіслати тестове повідомлення, щоб підтвердити налаштування."""
    _call(token, "sendMessage", chat_id=str(chat_id).strip(),
          text="✅ Dota Ready Helper налаштовано!")

# --- Запис .env ------------------------------------------------------------

def update_env_lines(lines: List[str], values: Dict[str, str]) -> List[str]:
    """
    Оновити значення ключів, зберігши решту рядків і коментарі.

    Ключі, яких у файлі немає, додаються в кінець.
    """
    remaining = dict(values)
    result = []

    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in remaining:
            result.append(f"{key}={remaining.pop(key)}")
        else:
            result.append(line.rstrip("\n"))

    if remaining:
        if result and result[-1].strip():
            result.append("")
        for key, value in remaining.items():
            result.append(f"{key}={value}")

    return result

def write_env(values: Dict[str, str], env_path: Path = ENV_PATH,
              template_path: Path = ENV_EXAMPLE_PATH) -> Path:
    """
    Записати значення у .env.

    Якщо файлу ще немає, за основу береться .env.example — так користувач
    отримує всі налаштування з коментарями та значеннями за замовчуванням.
    """
    if env_path.exists():
        source = env_path.read_text(encoding="utf-8").splitlines()
    elif template_path and template_path.exists():
        source = template_path.read_text(encoding="utf-8").splitlines()
    else:
        source = []

    lines = update_env_lines(source, values)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path

# --- Графічний майстер -----------------------------------------------------

def run_gui_setup(env_path: Path = ENV_PATH) -> bool:
    """
    Показати вікно налаштування.

    Returns:
        True якщо налаштування збережено
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QApplication, QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
        QLineEdit, QMessageBox, QPushButton, QVBoxLayout
    )

    class SetupDialog(QDialog):
        """Вікно початкового налаштування."""

        def __init__(self):
            super().__init__()
            self.saved = False
            self._build_ui()

        def _build_ui(self):
            self.setWindowTitle("Dota Ready Helper — налаштування")
            self.setMinimumWidth(520)

            layout = QVBoxLayout(self)

            hint = QLabel(
                "1. Створи бота через <a href='https://t.me/botfather'>@BotFather</a> "
                "і скопіюй токен.<br>"
                "2. Напиши своєму боту будь-яке повідомлення.<br>"
                "3. Натисни «Визначити автоматично» — chat ID підставиться сам."
            )
            hint.setOpenExternalLinks(True)
            hint.setWordWrap(True)
            hint.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(hint)

            form = QFormLayout()

            self.token_input = QLineEdit()
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.token_input.setPlaceholderText("123456789:AA...")
            self.token_input.textChanged.connect(self._update_state)
            form.addRow("Токен бота:", self.token_input)

            self.show_token = QCheckBox("Показати токен")
            self.show_token.toggled.connect(
                lambda shown: self.token_input.setEchoMode(
                    QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password
                )
            )
            form.addRow("", self.show_token)

            chat_row = QHBoxLayout()
            self.chat_input = QLineEdit()
            self.chat_input.setPlaceholderText("123456789")
            self.chat_input.textChanged.connect(self._update_state)
            self.detect_btn = QPushButton("Визначити автоматично")
            self.detect_btn.clicked.connect(self._detect_chat_id)
            chat_row.addWidget(self.chat_input)
            chat_row.addWidget(self.detect_btn)
            form.addRow("Chat ID:", chat_row)

            layout.addLayout(form)

            self.status = QLabel("")
            self.status.setWordWrap(True)
            layout.addWidget(self.status)

            buttons = QHBoxLayout()
            self.test_btn = QPushButton("Перевірити зв'язок")
            self.test_btn.clicked.connect(self._test_connection)
            self.save_btn = QPushButton("Зберегти")
            self.save_btn.setDefault(True)
            self.save_btn.clicked.connect(self._save)
            cancel_btn = QPushButton("Скасувати")
            cancel_btn.clicked.connect(self.reject)

            buttons.addWidget(self.test_btn)
            buttons.addStretch()
            buttons.addWidget(cancel_btn)
            buttons.addWidget(self.save_btn)
            layout.addLayout(buttons)

            self._load_existing(env_path)
            self._update_state()

        def _load_existing(self, path: Path):
            """Підставити вже збережені значення, якщо .env існує."""
            if not path.exists():
                return

            for line in path.read_text(encoding="utf-8").splitlines():
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if key == "TELEGRAM_BOT_TOKEN":
                    self.token_input.setText(value)
                elif key == "TELEGRAM_CHAT_ID":
                    self.chat_input.setText(value)

        def _token(self) -> str:
            return self.token_input.text().strip()

        def _chat_id(self) -> str:
            return self.chat_input.text().strip()

        def _update_state(self):
            """Кнопки активні лише коли дані схожі на правильні."""
            token_ok = is_valid_token(self._token())
            self.detect_btn.setEnabled(token_ok)
            self.test_btn.setEnabled(token_ok and is_valid_chat_id(self._chat_id()))
            self.save_btn.setEnabled(token_ok and is_valid_chat_id(self._chat_id()))

            if self._token() and not token_ok:
                self._set_status("⚠️ Токен має вигляд 123456789:AA...", error=True)
            elif self._chat_id() and not is_valid_chat_id(self._chat_id()):
                self._set_status("⚠️ Chat ID — це число", error=True)

        def _set_status(self, text: str, error: bool = False):
            self.status.setText(text)
            self.status.setStyleSheet("color: #c0392b;" if error else "color: #27ae60;")

        def _busy(self, active: bool, text: str = ""):
            for widget in (self.detect_btn, self.test_btn, self.save_btn):
                widget.setEnabled(not active and widget.isEnabled())
            if text:
                self._set_status(text)
            QApplication.processEvents()

        def _detect_chat_id(self):
            self._busy(True, "Шукаю твоє повідомлення...")
            try:
                self.chat_input.setText(fetch_chat_id(self._token()))
                self._set_status("✅ Chat ID визначено")
            except SetupError as e:
                self._set_status(f"❌ {e}", error=True)
            finally:
                self._busy(False)
                self._update_state()

        def _test_connection(self):
            self._busy(True, "Перевіряю...")
            try:
                username = fetch_bot_username(self._token())
                send_test_message(self._token(), self._chat_id())
                self._set_status(f"✅ Бот @{username} надіслав тестове повідомлення")
            except SetupError as e:
                self._set_status(f"❌ {e}", error=True)
            finally:
                self._busy(False)
                self._update_state()

        def _save(self):
            try:
                write_env({
                    "TELEGRAM_BOT_TOKEN": self._token(),
                    "TELEGRAM_CHAT_ID": self._chat_id(),
                }, env_path)
            except OSError as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося записати .env:\n{e}")
                return

            self.saved = True
            QMessageBox.information(
                self, "Готово",
                f"Налаштування збережено у {env_path.name}."
            )
            self.accept()

    app = QApplication.instance() or QApplication([])
    dialog = SetupDialog()
    dialog.exec()
    return dialog.saved

# --- Консольний запасний варіант -------------------------------------------

def run_console_setup(env_path: Path = ENV_PATH) -> bool:
    """Налаштування без графіки — якщо PyQt6 недоступний."""
    print("\n=== Початкове налаштування Dota Ready Helper ===")
    print("Створи бота через @BotFather (https://t.me/botfather) і скопіюй токен.\n")

    token = input("Токен бота: ").strip()
    if not is_valid_token(token):
        print("❌ Токен має вигляд 123456789:AA...")
        return False

    chat_id = input("Chat ID (Enter — визначити автоматично): ").strip()
    if not chat_id:
        print("Напиши боту будь-яке повідомлення у Telegram і натисни Enter...")
        input()
        try:
            chat_id = fetch_chat_id(token)
            print(f"✅ Chat ID: {chat_id}")
        except SetupError as e:
            print(f"❌ {e}")
            return False

    if not is_valid_chat_id(chat_id):
        print("❌ Chat ID — це число")
        return False

    try:
        send_test_message(token, chat_id)
        print("✅ Тестове повідомлення надіслано")
    except SetupError as e:
        print(f"⚠️ {e}")

    write_env({"TELEGRAM_BOT_TOKEN": token, "TELEGRAM_CHAT_ID": chat_id}, env_path)
    print(f"✅ Налаштування збережено у {env_path.name}")
    return True

def run_setup(env_path: Path = ENV_PATH) -> bool:
    """Показати майстер налаштування: у вікні, а якщо не вийде — у консолі."""
    try:
        return run_gui_setup(env_path)
    except ImportError:
        return run_console_setup(env_path)

if __name__ == "__main__":
    run_setup()
