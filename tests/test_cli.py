from __future__ import annotations

from duo_bot import build_parser, main


def test_keep_defaults():
    args = build_parser().parse_args(["keep"])
    assert args.command == "keep"
    assert args.lessons == 1
    assert args.force is False


def test_farm_defaults():
    args = build_parser().parse_args(["farm"])
    assert args.target_xp == 100
    assert args.max_lessons == 20
    assert args.dry_run is False


def test_notify_defaults():
    args = build_parser().parse_args(["notify"])
    assert args.status == "failure"
    assert args.title == "duo-bot"


def test_keep_without_token_fails(tmp_path, monkeypatch):
    monkeypatch.delenv("DUOLINGO_JWT", raising=False)
    code = main(
        [
            "keep",
            "--env",
            str(tmp_path / "missing.env"),
            "--log-file",
            str(tmp_path / "duo-bot.log"),
        ]
    )
    assert code == 1


def test_notify_without_telegram_succeeds(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    code = main(
        [
            "notify",
            "--status",
            "success",
            "--env",
            str(tmp_path / "missing.env"),
            "--log-file",
            str(tmp_path / "duo-bot.log"),
        ]
    )
    assert code == 0
