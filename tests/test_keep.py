from __future__ import annotations

from datetime import UTC, datetime

from duo_bot.keep import account_today, run_keep


class FakeKeepClient:
    def __init__(self, profile: dict):
        self.profile = profile
        self.created = 0
        self.submitted = 0

    def get_profile(self, sub: str, fields: str) -> dict:
        return self.profile

    def create_session(self, from_language: str, learning_language: str) -> dict:
        self.created += 1
        return {"id": "s1", "challenges": [{}] * 16}

    def submit_session(self, session: dict, **kwargs) -> dict:
        self.submitted += 1
        return {"xpGain": 17}


NOW = datetime(2026, 11, 9, 2, 0, tzinfo=UTC)  # 09:00 WIB on 2026-11-09


def profile(last_extended: str | None, timezone_name: str = "Asia/Jakarta") -> dict:
    return {
        "fromLanguage": "en",
        "learningLanguage": "es",
        "timezone": timezone_name,
        "streakData": {"currentStreak": {"lastExtendedDate": last_extended}},
    }


def test_account_today_uses_account_timezone():
    assert account_today("Asia/Jakarta", now=NOW) == "2026-11-09"
    assert account_today("UTC", now=NOW) == "2026-11-09"


def test_account_today_handles_unknown_timezone():
    assert account_today("Mars/Olympus", now=NOW) == "2026-11-09"


def test_skips_when_already_extended_today():
    client = FakeKeepClient(profile("2026-11-09"))
    result = run_keep(client, "sub", now=NOW, delay=0, jitter=0)
    assert result.ran is False
    assert client.created == 0
    assert "already extended" in result.reason


def test_runs_when_last_extended_is_yesterday():
    client = FakeKeepClient(profile("2026-11-08"))
    result = run_keep(client, "sub", now=NOW, delay=0, jitter=0)
    assert result.ran is True
    assert result.stats is not None
    assert result.stats.xp == 17
    assert client.submitted == 1


def test_force_runs_even_if_extended_today():
    client = FakeKeepClient(profile("2026-11-09"))
    result = run_keep(client, "sub", now=NOW, force=True, delay=0, jitter=0)
    assert result.ran is True
    assert client.submitted == 1


def test_dry_run_does_not_submit():
    client = FakeKeepClient(profile("2026-11-08"))
    result = run_keep(client, "sub", now=NOW, dry_run=True, delay=0, jitter=0)
    assert result.ran is True
    assert client.created == 1
    assert client.submitted == 0
