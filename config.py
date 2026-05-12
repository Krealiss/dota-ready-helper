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

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Шляхи до зображень
IMG_SEARCHING = ASSETS_DIR / "is_searching_game.png"
IMG_SEARCH_BTN = ASSETS_DIR / "search_game.png"
IMG_ACCEPT = ASSETS_DIR / "prinyat.png"
IMG_STOP = ASSETS_DIR / "stop.png"

# Параметри розпізнавання
CONFIDENCE = {
    "accept": float(os.getenv("CONFIDENCE_ACCEPT", "0.80")),
    "searching": float(os.getenv("CONFIDENCE_SEARCHING", "0.70")),
    "search_btn": float(os.getenv("CONFIDENCE_SEARCH_BTN", "0.70")),
    "stop_btn": float(os.getenv("CONFIDENCE_STOP_BTN", "0.75")),
}

# Таймінги
SCAN_INTERVAL = float(os.getenv("SCAN_INTERVAL", "0.30"))
CLICK_COOLDOWN = float(os.getenv("CLICK_COOLDOWN", "1.00"))
MESSAGE_COOLDOWN = float(os.getenv("MESSAGE_COOLDOWN", "5.00"))

# Регіон пошуку (None = весь екран)
SEARCH_REGION: Optional[tuple] = None

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
