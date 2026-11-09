from __future__ import annotations

import pytest

import duo_bot.notify as notify_module
from duo_bot.notify import (
    build_message,
    notify,
    send_telegram,
    tail_log,
)


class FakeTelegramResponse:
    def __init__(self, status: int, payload: dict | None = None):
        self.status_code = status
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


@pytest.fixture(autouse=True)
def clean_telegram_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(notify_module.time, "sleep", lambda _seconds: None)


def test_build_message_redacts_secrets():
    message = build_message(
        "success",
        "Bearer abc.def.ghi and token bot123456:ABCDEFGHIJKLMNOPQRSTUVWX",
    )
    assert message.startswith("✅ duo-bot: success")
    assert "abc.def.ghi" not in message
    assert "bot123456" not in message


def test_send_without_config_is_noop():
    assert send_telegram("hello") is False


def test_send_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeTelegramResponse(200, {"ok": True})

    monkeypatch.setattr(notify_module.requests, "post", fake_post)
    assert send_telegram("hello") is True
    assert calls[0][1]["json"]["chat_id"] == "42"
    assert calls[0][1]["json"]["text"] == "hello"


def test_send_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    responses = [FakeTelegramResponse(500), FakeTelegramResponse(200, {"ok": True})]
    monkeypatch.setattr(notify_module.requests, "post", lambda *a, **k: responses.pop(0))
    assert send_telegram("hello", retries=1) is True


def test_send_gives_up(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(notify_module.requests, "post", lambda *a, **k: FakeTelegramResponse(400))
    assert send_telegram("hello", retries=0) is False


def test_notify_always_sends(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(
        notify_module.requests, "post", lambda *a, **k: FakeTelegramResponse(200, {"ok": True})
    )
    assert notify("success") is True
    assert notify("failure") is True


def test_tail_log(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("\n".join(f"line {i}" for i in range(20)), encoding="utf-8")
    assert tail_log(log, lines=2) == "line 18\nline 19"
    assert tail_log(tmp_path / "missing.log") == ""
