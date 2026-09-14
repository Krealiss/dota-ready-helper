# -*- coding: utf-8 -*-
"""Конфігурація Dota Ready Helper."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Завантажити змінні з .env
load_dotenv()

# Базові шляхи
BASE_DIR = Path(__file__).parent.absolute()
ASSETS_DIR = BASE_DIR / "assets"

# Версія програми — єдине джерело правди
APP_VERSION = "2.1"

def _env_float(name: str, default: float) -> float:
    """Прочитати число з .env, не падаючи на некоректному значенні."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"⚠️ {name}={raw!r} — не число, використано {default}")
        return default

def _env_int(name: str, default: int) -> int:
    """Прочитати ціле число з .env, не падаючи на некоректному значенні."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"⚠️ {name}={raw!r} — не ціле число, використано {default}")
        return default

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Імена готових PNG тут навмисно не дублюються: вони потрібні лише майстру
# як підказка для автопошуку, і єдине їх місце — calibration_wizard.SHIPPED.

# Параметри розпізнавання. Ключ відповідає імені елемента калібрування
# (calibration.ELEMENTS); "stop_btn" перейменовано на "stop", але змінна
# оточення лишається CONFIDENCE_STOP_BTN заради сумісності .env.
CONFIDENCE = {
    "accept": _env_float("CONFIDENCE_ACCEPT", 0.80),
    "searching": _env_float("CONFIDENCE_SEARCHING", 0.70),
    "search_btn": _env_float("CONFIDENCE_SEARCH_BTN", 0.70),
    "stop": _env_float("CONFIDENCE_STOP_BTN", 0.75),
}

# Таймінги
SCAN_INTERVAL = _env_float("SCAN_INTERVAL", 0.30)
CLICK_COOLDOWN = _env_float("CLICK_COOLDOWN", 1.00)
MESSAGE_COOLDOWN = _env_float("MESSAGE_COOLDOWN", 5.00)

# Калібрування
CALIBRATION_DIR = BASE_DIR / "calibration"

# Куди бот складає кадри з вікном прийняття для корпусу реальних знімків.
# Окрема константа, а не шлях від __file__: інакше тести пишуть у справжню
# теку проєкту і підкладають синтетичний макет замість кадру користувача.
CORPUS_DIR = BASE_DIR / "diagnostics" / "corpus"

# Пауза між перевірками, коли Dota не запущена
NO_GAME_POLL_INTERVAL = _env_float("NO_GAME_POLL_INTERVAL", 2.0)

# Резервний пошук кнопки за кольором, якщо жоден шаблон не збігся
ACCEPT_COLOR_FALLBACK = os.getenv("ACCEPT_COLOR_FALLBACK", "1").strip().lower() in (
    "1", "true", "yes", "on"
)

def credentials_present() -> bool:
    """Чи заповнені дані Telegram — те, що вміє полагодити майстер налаштування."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

def validate_config() -> bool:
    """
    Перевірити, чи всі необхідні налаштування присутні.

    Готові PNG у assets/ тут не перевіряються: після переходу на
    калібрування вони лише підказка всередині майстра, а
    calibration_wizard.shipped_templates() і так спокійно пропускає
    відсутні файли. Вимагати їх для старту означало б не запустити
    програму через відсутню підказку — і зламати збірку .exe без assets/
    ще до коду, здатного пояснити причину.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не встановлено у .env")
        return False
    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID не встановлено у .env")
        return False

    return True
