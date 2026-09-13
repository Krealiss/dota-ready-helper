# -*- coding: utf-8 -*-
"""Майстер налаштування: валідація, розбір відповіді Telegram і запис .env."""
import pytest

import setup_dialog as sd

VALID_TOKEN = "123456789:AAH" + "x" * 30


@pytest.mark.parametrize("token,expected", [
    (VALID_TOKEN, True),
    (f"  {VALID_TOKEN}  ", True),
    ("123456789:AAH-short", False),
    ("без двокрапки", False),
    ("", False),
    (None, False),
    ("abc:" + "x" * 35, False),
])
def test_is_valid_token(token, expected):
    assert sd.is_valid_token(token) is expected


@pytest.mark.parametrize("chat_id,expected", [
    ("123456789", True),
    (123456789, True),
    ("-1001234567890", True),      # група
    ("  123456789 ", True),
    ("не число", False),
    ("123", False),
    ("", False),
    (None, False),
])
def test_is_valid_chat_id(chat_id, expected):
    assert sd.is_valid_chat_id(chat_id) is expected


def test_parse_chat_id_takes_latest_message():
    payload = {"ok": True, "result": [
        {"update_id": 1, "message": {"chat": {"id": 111}, "text": "привіт"}},
        {"update_id": 2, "message": {"chat": {"id": 222}, "text": "ще раз"}},
    ]}

    assert sd.parse_chat_id(payload) == "222"


@pytest.mark.parametrize("payload", [
    {"ok": True, "result": []},
    {"ok": True},
    {},
    None,
])
def test_parse_chat_id_without_messages(payload):
    assert sd.parse_chat_id(payload) is None


@pytest.mark.parametrize("key", ["edited_message", "channel_post"])
def test_parse_chat_id_other_update_types(key):
    payload = {"result": [{"update_id": 1, key: {"chat": {"id": -100500}}}]}

    assert sd.parse_chat_id(payload) == "-100500"


def test_parse_chat_id_from_callback_query():
    payload = {"result": [
        {"update_id": 1, "callback_query": {"message": {"chat": {"id": 777}}}}
    ]}

    assert sd.parse_chat_id(payload) == "777"


def test_update_env_lines_keeps_comments_and_other_keys():
    lines = [
        "# Telegram",
        "TELEGRAM_BOT_TOKEN=old_token",
        "TELEGRAM_CHAT_ID=old_chat",
        "",
        "# Timings",
        "SCAN_INTERVAL=0.30",
    ]

    result = sd.update_env_lines(lines, {
        "TELEGRAM_BOT_TOKEN": "new_token",
        "TELEGRAM_CHAT_ID": "new_chat",
    })

    assert result == [
        "# Telegram",
        "TELEGRAM_BOT_TOKEN=new_token",
        "TELEGRAM_CHAT_ID=new_chat",
        "",
        "# Timings",
        "SCAN_INTERVAL=0.30",
    ]


def test_update_env_lines_appends_missing_keys():
    result = sd.update_env_lines(["SCAN_INTERVAL=0.30"],
                                 {"TELEGRAM_CHAT_ID": "123456789"})

    assert result[0] == "SCAN_INTERVAL=0.30"
    assert "TELEGRAM_CHAT_ID=123456789" in result


def test_write_env_creates_file_from_template(tmp_path):
    template = tmp_path / ".env.example"
    template.write_text(
        "# Telegram Bot Configuration\n"
        "TELEGRAM_BOT_TOKEN=your_bot_token_here\n"
        "TELEGRAM_CHAT_ID=your_chat_id_here\n"
        "\n"
        "SCAN_INTERVAL=0.30\n",
        encoding="utf-8"
    )
    env = tmp_path / ".env"

    sd.write_env({"TELEGRAM_BOT_TOKEN": VALID_TOKEN, "TELEGRAM_CHAT_ID": "123456789"},
                 env_path=env, template_path=template)

    text = env.read_text(encoding="utf-8")
    assert f"TELEGRAM_BOT_TOKEN={VALID_TOKEN}" in text
    assert "TELEGRAM_CHAT_ID=123456789" in text
    assert "your_bot_token_here" not in text
    assert "# Telegram Bot Configuration" in text      # коментарі з шаблону
    assert "SCAN_INTERVAL=0.30" in text                # решта налаштувань


def test_write_env_updates_existing_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text("TELEGRAM_BOT_TOKEN=old\nTELEGRAM_CHAT_ID=old\n"
                   "CONFIDENCE_ACCEPT=0.65\n", encoding="utf-8")

    sd.write_env({"TELEGRAM_CHAT_ID": "987654321"}, env_path=env, template_path=None)

    text = env.read_text(encoding="utf-8")
    assert "TELEGRAM_CHAT_ID=987654321" in text
    assert "TELEGRAM_BOT_TOKEN=old" in text
    assert "CONFIDENCE_ACCEPT=0.65" in text            # чужі налаштування не зачеплені


def test_write_env_without_template(tmp_path):
    env = tmp_path / ".env"

    sd.write_env({"TELEGRAM_BOT_TOKEN": VALID_TOKEN}, env_path=env,
                 template_path=tmp_path / "missing.example")

    assert env.read_text(encoding="utf-8").strip() == f"TELEGRAM_BOT_TOKEN={VALID_TOKEN}"


def test_fetch_chat_id_reports_missing_messages(monkeypatch):
    """Користувач ще не написав боту — має бути зрозуміла підказка."""
    class Response:
        @staticmethod
        def json():
            return {"ok": True, "result": []}

    monkeypatch.setattr(sd.requests, "get", lambda *a, **kw: Response())

    with pytest.raises(sd.SetupError, match="Напиши боту"):
        sd.fetch_chat_id(VALID_TOKEN)


def test_fetch_bot_username(monkeypatch):
    class Response:
        @staticmethod
        def json():
            return {"ok": True, "result": {"username": "my_test_bot"}}

    monkeypatch.setattr(sd.requests, "post", lambda *a, **kw: Response())

    assert sd.fetch_bot_username(VALID_TOKEN) == "my_test_bot"


def test_telegram_error_is_reported(monkeypatch):
    class Response:
        @staticmethod
        def json():
            return {"ok": False, "description": "Unauthorized"}

    monkeypatch.setattr(sd.requests, "post", lambda *a, **kw: Response())

    with pytest.raises(sd.SetupError, match="Unauthorized"):
        sd.fetch_bot_username("123456789:" + "x" * 35)


def test_network_failure_is_reported(monkeypatch):
    def boom(*args, **kwargs):
        raise sd.requests.RequestException("timeout")

    monkeypatch.setattr(sd.requests, "post", boom)

    with pytest.raises(sd.SetupError, match="Немає зв'язку"):
        sd.fetch_bot_username(VALID_TOKEN)
