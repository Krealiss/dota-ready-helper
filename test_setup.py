# -*- coding: utf-8 -*-
"""Тестовий скрипт для перевірки конфігурації."""
import sys
import os
from pathlib import Path

# Виправлення кодування для Windows
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8')

def test_imports():
    """Перевірити, чи всі модулі імпортуються."""
    print("Перевірка імпортів...")
    try:
        import pyautogui
        import keyboard
        import requests
        import telebot
        from PIL import Image
        from dotenv import load_dotenv
        print("[OK] Всі залежності встановлено")
        return True
    except ImportError as e:
        print(f"[FAIL] Відсутня залежність: {e}")
        print("\nВстанови залежності:")
        print("pip install -r requirements.txt")
        return False

def test_config():
    """Перевірити конфігурацію."""
    print("\nПеревірка конфігурації...")
    try:
        from config import validate_config
        if validate_config():
            print("[OK] Конфігурація валідна")
            return True
        else:
            print("[FAIL] Помилка конфігурації")
            return False
    except Exception as e:
        print(f"[FAIL] Помилка: {e}")
        return False

def test_images():
    """Перевірити наявність зображень."""
    print("\nПеревірка зображень...")
    from config import IMG_SEARCHING, IMG_SEARCH_BTN, IMG_ACCEPT, IMG_STOP
    from image_recognition import validate_image

    images = {
        "is_searching_game.png": IMG_SEARCHING,
        "search_game.png": IMG_SEARCH_BTN,
        "prinyat.png": IMG_ACCEPT,
        "stop.png": IMG_STOP,
    }

    all_ok = True
    for name, path in images.items():
        if validate_image(path):
            print(f"  [OK] {name}")
        else:
            print(f"  [FAIL] {name}")
            all_ok = False

    return all_ok

def test_telegram():
    """Перевірити підключення до Telegram."""
    print("\nПеревірка Telegram...")
    try:
        from config import TELEGRAM_BOT_TOKEN
        import requests

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_name = data["result"]["username"]
                print(f"[OK] Підключено до бота: @{bot_name}")
                return True
            else:
                print("[FAIL] Невалідний токен")
                return False
        else:
            print(f"[FAIL] Помилка API: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Помилка: {e}")
        return False

def main():
    """Запустити всі тести."""
    print("=" * 50)
    print("Тестування Dota Ready Helper v2.0")
    print("=" * 50)

    results = []
    results.append(("Імпорти", test_imports()))
    results.append(("Конфігурація", test_config()))
    results.append(("Зображення", test_images()))
    results.append(("Telegram", test_telegram()))

    print("\n" + "=" * 50)
    print("Результати:")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "[OK]  " if passed else "[FAIL]"
        print(f"{status} {name}")
        if not passed:
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("\nВсі тести пройдено! Можеш запускати бота.")
        print("\nЗапуск:")
        print("  python main.py")
        print("або")
        print("  start.bat")
        return 0
    else:
        print("\nДеякі тести не пройдено. Виправ помилки перед запуском.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nПерервано користувачем")
        sys.exit(1)
