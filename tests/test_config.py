from __future__ import annotations

import os

import pytest

from duo_bot.config import (
    configure_timezone,
    get_bool,
    get_float,
    get_int,
    load_env,
    require_token,
)
from duo_bot.errors import ConfigError


def test_load_env_supports_quotes_export_and_comments(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "# comment",
                "PLAIN=value",
                "export EXPORTED=yes",
                'QUOTED="hello world"',
                "SINGLE='single value'",
                "TRAILING=abc # note",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for key in ("PLAIN", "EXPORTED", "QUOTED", "SINGLE", "TRAILING"):
        monkeypatch.delenv(key, raising=False)

    load_env(env)

    assert os.environ["PLAIN"] == "value"
    assert os.environ["EXPORTED"] == "yes"
    assert os.environ["QUOTED"] == "hello world"
    assert os.environ["SINGLE"] == "single value"
    assert os.environ["TRAILING"] == "abc"


def test_load_env_does_not_override_by_default(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("KEY=from_file\n", encoding="utf-8")
    monkeypatch.setenv("KEY", "from_env")

    load_env(env)
    assert os.environ["KEY"] == "from_env"

    load_env(env, override=True)
    assert os.environ["KEY"] == "from_file"


def test_load_env_missing_file_is_a_noop(tmp_path):
    load_env(tmp_path / "missing.env")


def test_typed_getters(monkeypatch):
    monkeypatch.setenv("AN_INT", "42")
    monkeypatch.setenv("A_FLOAT", "1.5")
    monkeypatch.setenv("A_BOOL", "yes")
    assert get_int("AN_INT", 0) == 42
    assert get_float("A_FLOAT", 0.0) == 1.5
    assert get_bool("A_BOOL") is True
    assert get_int("MISSING", 7) == 7


def test_typed_getters_reject_garbage(monkeypatch):
    monkeypatch.setenv("BAD", "nope")
    with pytest.raises(ConfigError):
        get_int("BAD", 0)
    with pytest.raises(ConfigError):
        get_float("BAD", 0.0)


def test_require_token(monkeypatch):
    monkeypatch.delenv("DUOLINGO_JWT", raising=False)
    with pytest.raises(ConfigError):
        require_token()
    monkeypatch.setenv("DUOLINGO_JWT", "  abc.def.ghi  ")
    assert require_token() == "abc.def.ghi"


def test_configure_timezone_sets_env(monkeypatch):
    monkeypatch.delenv("TZ", raising=False)
    assert configure_timezone("Asia/Jakarta") == "Asia/Jakarta"
    assert os.environ["TZ"] == "Asia/Jakarta"
    assert configure_timezone(None) == "Asia/Jakarta"
