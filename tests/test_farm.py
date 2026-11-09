from __future__ import annotations

import pytest

from duo_bot.errors import AuthError
from duo_bot.farm import run_farm
from duo_bot.sessions import Course

COURSE = Course("en", "es")


class FakeLessonClient:
    def __init__(self, gains: list[int], *, fail_on=(), auth_on=()):
        self.gains = list(gains)
        self.fail_on = set(fail_on)
        self.auth_on = set(auth_on)
        self.calls = 0
        self.submitted = 0

    def create_session(self, from_language: str, learning_language: str) -> dict:
        self.calls += 1
        if self.calls in self.auth_on:
            raise AuthError("unauthorized")
        if self.calls in self.fail_on:
            raise RuntimeError("boom")
        return {"id": f"s{self.calls}", "challenges": [{}] * 16}

    def submit_session(self, session: dict, **kwargs) -> dict:
        self.submitted += 1
        gain = self.gains.pop(0) if self.gains else 0
        return {"xpGain": gain}


def farm(client, **kwargs):
    defaults = {
        "target_xp": 1000,
        "max_lessons": 10,
        "max_minutes": 5,
        "delay": 0,
        "jitter": 0,
        "max_failures": 3,
        "stop_after_zero": 3,
    }
    defaults.update(kwargs)
    return run_farm(client, COURSE, **defaults)


def test_stops_when_target_reached():
    client = FakeLessonClient([17, 17, 17])
    stats = farm(client, target_xp=34)
    assert stats.lessons == 2
    assert stats.xp == 34
    assert client.submitted == 2


def test_stops_at_lesson_cap():
    client = FakeLessonClient([17] * 20)
    stats = farm(client, max_lessons=2)
    assert stats.lessons == 2
    assert stats.xp == 34


def test_stops_after_consecutive_zero_xp():
    client = FakeLessonClient([0, 0, 0, 17])
    stats = farm(client, stop_after_zero=3, max_lessons=10)
    assert stats.lessons == 3
    assert stats.xp == 0
    assert stats.zero_xp_streak == 3


def test_zero_xp_streak_resets():
    client = FakeLessonClient([0, 17, 0, 17, 17])
    stats = farm(client, stop_after_zero=2, max_lessons=5, target_xp=10_000)
    assert stats.lessons == 5
    assert stats.xp == 51


def test_dry_run_does_not_submit():
    client = FakeLessonClient([17, 17, 17])
    stats = farm(client, dry_run=True, max_lessons=2)
    assert stats.lessons == 2
    assert stats.xp == 0
    assert client.submitted == 0


def test_stops_after_max_failures():
    client = FakeLessonClient([17], fail_on={1, 2})
    stats = farm(client, max_failures=2)
    assert stats.failures == 2
    assert stats.lessons == 2


def test_auth_error_propagates():
    client = FakeLessonClient([17], auth_on={1})
    with pytest.raises(AuthError):
        farm(client)
    assert client.submitted == 0
