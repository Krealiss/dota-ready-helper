# -*- coding: utf-8 -*-
"""Telegram бот для керування Dota Ready Helper."""
import time
import threading
from functools import wraps
from typing import Optional, Callable
import requests
import telebot
from telebot import types

from logger import logger
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def is_authorized(chat_id) -> bool:
    """
    Перевірити, чи chat_id належить власнику бота.

    Бот керує мишею на ПК, тому будь-хто, хто знає ім'я бота, не повинен
    мати доступу до команд — приймаємо лише TELEGRAM_CHAT_ID з .env.
    """
    if chat_id is None or not TELEGRAM_CHAT_ID:
        return False
    return str(chat_id).strip() == str(TELEGRAM_CHAT_ID).strip()

class TelegramBot:
    """Telegram бот з динамічним меню."""

    def __init__(self):
        self.bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        self._last_menu_msg_id: Optional[int] = None
        self._menu_lock = threading.Lock()

        # Callback'и для кнопок
        self.on_start_callback: Optional[Callable] = None
        self.on_stop_callback: Optional[Callable] = None
        self.on_stats_callback: Optional[Callable] = None
        self.on_export_callback: Optional[Callable] = None

        self._setup_handlers()

    def _require_owner(self, handler: Callable) -> Callable:
        """Декоратор: виконувати команду лише для власника бота."""

        @wraps(handler)
        def wrapper(message):
            chat_id = getattr(getattr(message, "chat", None), "id", None)
            if not is_authorized(chat_id):
                logger.warning(f"[TG] Проігноровано команду від chat_id={chat_id}")
                return None
            return handler(message)

        return wrapper

    def _require_owner_call(self, handler: Callable) -> Callable:
        """Декоратор: обробляти натискання кнопки лише від власника бота."""

        @wraps(handler)
        def wrapper(call):
            chat = getattr(getattr(call, "message", None), "chat", None)
            chat_id = getattr(chat, "id", None)
            if not is_authorized(chat_id):
                logger.warning(f"[TG] Відхилено кнопку від chat_id={chat_id}")
                try:
                    self.bot.answer_callback_query(call.id, "⛔ Доступ заборонено")
                except Exception:
                    pass
                return None
            return handler(call)

        return wrapper

    def _setup_handlers(self):
        """Налаштувати обробники команд та кнопок."""

        @self.bot.message_handler(commands=['start', 'menu'])
        @self._require_owner
        def handle_menu(message):
            self.send_menu('idle')

        @self.bot.message_handler(commands=['status'])
        @self._require_owner
        def handle_status(message):
            self.send_message("ℹ️ Бот активний. Використовуй /menu для керування.")

        @self.bot.message_handler(commands=['stats'])
        @self._require_owner
        def handle_stats(message):
            if self.on_stats_callback:
                self.on_stats_callback()
            else:
                self.send_message("📊 Статистика недоступна.")

        @self.bot.message_handler(commands=['export'])
        @self._require_owner
        def handle_export(message):
            if self.on_export_callback:
                self.on_export_callback()
            else:
                self.send_message("📥 Експорт недоступний.")

        @self.bot.callback_query_handler(func=lambda call: call.data == "start_search")
        @self._require_owner_call
        def on_start(call):
            try:
                self.bot.answer_callback_query(call.id)
            except Exception:
                pass

            if self.on_start_callback:
                self.on_start_callback()
                self.send_message("⏳ Запускаю пошук гри на ПК...")
            else:
                self.send_message("❌ Помилка: callback не налаштовано.")

        @self.bot.callback_query_handler(func=lambda call: call.data == "stop_search")
        @self._require_owner_call
        def on_stop(call):
            try:
                self.bot.answer_callback_query(call.id)
            except Exception:
                pass

            if self.on_stop_callback:
                self.on_stop_callback()
                self.send_message("⏳ Зупиняю пошук гри на ПК...")
            else:
                self.send_message("❌ Помилка: callback не налаштовано.")

    def _build_menu(self, state: str) -> types.InlineKeyboardMarkup:
        """
        Побудувати меню залежно від стану.

        Args:
            state: 'no_game', 'idle', 'searching', або 'ready'
        """
        kb = types.InlineKeyboardMarkup()

        if state == "no_game":
            return kb
        if state == "searching":
            kb.add(types.InlineKeyboardButton("⏹ Зупинити пошук",
                                              callback_data="stop_search"))
        else:
            kb.add(types.InlineKeyboardButton("🔁 Запустити пошук",
                                              callback_data="start_search"))
        return kb

    def _menu_text(self, state: str) -> str:
        """Текст меню залежно від стану."""
        if state == "no_game":
            return "🎮 Dota 2 не запущена.\nЗапусти гру — меню з'явиться саме."
        if state == "searching":
            return ("🔎 Пошук гри активний.\n"
                    "Бот автоматично натисне «Прийняти» при знаходженні матчу.")
        if state == "ready":
            return "✅ Матч знайдено!\nНатискаю «Прийняти»..."
        return "⏹ Пошук не активний.\nМожеш запустити пошук гри."

    def send_menu(self, state: str):
        """Надіслати або оновити меню."""
        with self._menu_lock:
            kb = self._build_menu(state)
            text = self._menu_text(state)

            try:
                if self._last_menu_msg_id:
                    self.bot.edit_message_text(
                        chat_id=TELEGRAM_CHAT_ID,
                        message_id=self._last_menu_msg_id,
                        text=text,
                        reply_markup=kb
                    )
                else:
                    msg = self.bot.send_message(
                        TELEGRAM_CHAT_ID,
                        text,
                        reply_markup=kb
                    )
                    self._last_menu_msg_id = msg.message_id
            except Exception as e:
                # Якщо не вдалось відредагувати — надсилаємо нове
                try:
                    msg = self.bot.send_message(
                        TELEGRAM_CHAT_ID,
                        text,
                        reply_markup=kb
                    )
                    self._last_menu_msg_id = msg.message_id
                except Exception as e:
                    logger.error(f"Помилка відправки меню: {e}")

    def send_message(self, text: str):
        """Надіслати текстове повідомлення."""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
                timeout=5
            )
            logger.info(f"[TG] {text}")
        except Exception as e:
            logger.error(f"Помилка відправки повідомлення: {e}")

    def start_polling(self):
        """Запустити polling у фоновому режимі."""
        def _run():
            # Вимкнути webhook
            try:
                self.bot.remove_webhook(drop_pending_updates=False)
                requests.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook",
                    timeout=5
                )
            except Exception:
                pass

            time.sleep(1)
            self.send_menu('idle')

            logger.info("Telegram бот запущено")
            self.bot.infinity_polling(timeout=30, long_polling_timeout=30)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread
