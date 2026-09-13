# -*- coding: utf-8 -*-
"""Конфігурація Dota Ready Helper."""
import os
from pathlib import Path
from typing import Optional
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

# Шляхи до зображень
IMG_SEARCHING = ASSETS_DIR / "is_searching_game.png"
IMG_SEARCH_BTN = ASSETS_DIR / "search_game.png"
IMG_ACCEPT = ASSETS_DIR / "prinyat.png"
IMG_STOP = ASSETS_DIR / "stop.png"

# Усі варіанти кнопки "Прийняти" (prinyat.png, prinyat_allpick.png, ...).
# Достатньо покласти новий вирізаний скриншот кнопки у assets/ з префіксом prinyat.
IMG_ACCEPT_VARIANTS = sorted(ASSETS_DIR.glob("prinyat*.png"))

# Параметри розпізнавання
CONFIDENCE = {
    "accept": _env_float("CONFIDENCE_ACCEPT", 0.80),
    "searching": _env_float("CONFIDENCE_SEARCHING", 0.70),
    "search_btn": _env_float("CONFIDENCE_SEARCH_BTN", 0.70),
    "stop_btn": _env_float("CONFIDENCE_STOP_BTN", 0.75),
}

# Таймінги
SCAN_INTERVAL = _env_float("SCAN_INTERVAL", 0.30)
CLICK_COOLDOWN = _env_float("CLICK_COOLDOWN", 1.00)
MESSAGE_COOLDOWN = _env_float("MESSAGE_COOLDOWN", 5.00)

# Регіон пошуку (None = весь екран)
SEARCH_REGION: Optional[tuple] = None

# Регіон пошуку кнопки "Прийняти" (центр екрана).
# Вікно "Ваша гра готова" з деталями матчу вище за старе, тому регіон більший.
ACCEPT_REGION_WIDTH = _env_int("ACCEPT_REGION_WIDTH", 1000)
ACCEPT_REGION_HEIGHT = _env_int("ACCEPT_REGION_HEIGHT", 600)

# Резервний пошук кнопки за кольором, якщо жоден шаблон не збігся
ACCEPT_COLOR_FALLBACK = os.getenv("ACCEPT_COLOR_FALLBACK", "1").strip().lower() in (
    "1", "true", "yes", "on"
)

def credentials_present() -> bool:
    """Чи заповнені дані Telegram — те, що вміє полагодити майстер налаштування."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

def validate_config() -> bool:
    """Перевірити, чи всі необхідні налаштування присутні."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не встановлено у .env")
        return False
    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID не встановлено у .env")
        return False

    # Перевірка наявності зображень
    for img_name, img_path in [
        ("is_searching_game.png", IMG_SEARCHING),
        ("search_game.png", IMG_SEARCH_BTN),
        ("prinyat.png", IMG_ACCEPT),
        ("stop.png", IMG_STOP),
    ]:
        if not img_path.exists():
            print(f"❌ Зображення не знайдено: {img_path}")
            return False

    return True
