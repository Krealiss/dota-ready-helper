# -*- coding: utf-8 -*-
"""Доступ до бота має бути лише у власника — бот керує мишею на ПК."""
from types import SimpleNamespace

import pytest

import telegram_bot as tb

OWNER = "123456789"
STRANGER = "999999999"
FAKE_TOKEN = "123456:AAtest-token-for-unit-tests"


def message(chat_id, text="/start"):
    return SimpleNamespace(chat=SimpleNamespace(id=chat_id), text=text,
                           from_user=SimpleNamespace(id=chat_id))


def callback(chat_id, data):
    return SimpleNamespace(id="cb1", data=data, message=message(chat_id),
                           from_user=SimpleNamespace(id=chat_id))


@pytest.fixture
def bot(monkeypatch):
    """Бот із перехопленими виходами — жодних мережевих запитів."""
    monkeypatch.setattr(tb, "TELEGRAM_BOT_TOKEN", FAKE_TOKEN)
    monkeypatch.setattr(tb, "TELEGRAM_CHAT_ID", OWNER)

    instance = tb.TelegramBot()
    calls = {"messages": [], "menus": [], "answers": [],
             "start": 0, "stop": 0, "stats": 0, "export": 0}

    instance.send_message = lambda text: calls["messages"].append(text)
    instance.send_menu = lambda state: calls["menus"].append(state)
    instance.bot.answer_callback_query = \
        lambda cid, text=None, **kw: calls["answers"].append(text)

    for key in ("start", "stop", "stats", "export"):
        setattr(instance, f"on_{key}_callback",
                (lambda k: lambda: calls.__setitem__(k, calls[k] + 1))(key))

    instance.calls = calls
    return instance


def command(bot, name):
    for handler in bot.bot.message_handlers:
        if name in handler["filters"].get("commands", []):
            return handler["function"]
    raise AssertionError(f"обробник /{name} не зареєстровано")


def button(bot, data):
    for handler in bot.bot.callback_query_handlers:
        if handler["filters"]["func"](SimpleNamespace(data=data)):
            return handler["function"]
    raise AssertionError(f"обробник кнопки {data} не зареєстровано")


@pytest.mark.parametrize("chat_id,expected", [
    (OWNER, True),
    (int(OWNER), True),
    (f" {OWNER} ", True),
    (STRANGER, False),
    (OWNER[:-1], False),
    (None, False),
    ("", False),
])
def test_is_authorized(monkeypatch, chat_id, expected):
    monkeypatch.setattr(tb, "TELEGRAM_CHAT_ID", OWNER)
    assert tb.is_authorized(chat_id) is expected


def test_is_authorized_without_configured_chat_id(monkeypatch):
    """Порожній TELEGRAM_CHAT_ID не повинен відкривати доступ усім."""
    monkeypatch.setattr(tb, "TELEGRAM_CHAT_ID", "")
    assert tb.is_authorized(STRANGER) is False
    assert tb.is_authorized("") is False


@pytest.mark.parametrize("name", ["start", "status", "stats", "export"])
def test_stranger_commands_are_ignored(bot, name):
    command(bot, name)(message(STRANGER, f"/{name}"))

    assert bot.calls["messages"] == []
    assert bot.calls["menus"] == []
    assert bot.calls["stats"] == 0
    assert bot.calls["export"] == 0


@pytest.mark.parametrize("data", ["start_search", "stop_search"])
def test_stranger_cannot_control_the_pc(bot, data):
    button(bot, data)(callback(STRANGER, data))

    assert bot.calls["start"] == 0
    assert bot.calls["stop"] == 0
    assert bot.calls["answers"] == ["⛔ Доступ заборонено"]


def test_owner_commands_work(bot):
    command(bot, "start")(message(OWNER, "/start"))
    command(bot, "status")(message(OWNER, "/status"))
    command(bot, "stats")(message(OWNER, "/stats"))
    command(bot, "export")(message(OWNER, "/export"))

    assert bot.calls["menus"] == ["idle"]
    assert len(bot.calls["messages"]) == 1
    assert bot.calls["stats"] == 1
    assert bot.calls["export"] == 1


def test_owner_buttons_work(bot):
    button(bot, "start_search")(callback(OWNER, "start_search"))
    button(bot, "stop_search")(callback(OWNER, "stop_search"))

    assert bot.calls["start"] == 1
    assert bot.calls["stop"] == 1
    # підтвердження без тексту прибирає "годинник" на кнопці
    assert bot.calls["answers"] == [None, None]
