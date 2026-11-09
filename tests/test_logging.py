from __future__ import annotations

from duo_bot.logging import summary_table, write_step_summary


def test_summary_table_renders_rows():
    table = summary_table("title", {"lessons": 1, "xp": 17})
    assert "### title" in table
    assert "| lessons | 1 |" in table
    assert "| xp | 17 |" in table


def test_write_step_summary(tmp_path, monkeypatch):
    target = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(target))
    assert write_step_summary("hello") is True
    assert target.read_text(encoding="utf-8") == "hello\n"


def test_write_step_summary_without_env(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert write_step_summary("hello") is False
