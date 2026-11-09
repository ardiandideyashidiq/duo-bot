from __future__ import annotations

import pytest

from duo_bot.errors import Abort
from duo_bot.sessions import Course, create_lesson, submit_lesson


class FakeClient:
    def __init__(self, session: dict | None = None, result: dict | None = None):
        self.session = session if session is not None else {"id": "abc", "challenges": [{}, {}]}
        self.result = result if result is not None else {"xpGain": 17}
        self.created = 0
        self.submitted = 0

    def create_session(self, from_language: str, learning_language: str) -> dict:
        self.created += 1
        return self.session

    def submit_session(self, session: dict, **kwargs) -> dict:
        self.submitted += 1
        return self.result


def test_course_from_profile():
    assert Course.from_profile({"fromLanguage": "en", "learningLanguage": "es"}) == Course(
        "en", "es"
    )


def test_course_from_profile_requires_languages():
    with pytest.raises(Abort):
        Course.from_profile({"fromLanguage": "en"})


def test_create_lesson():
    lesson = create_lesson(FakeClient(), Course("en", "es"))
    assert lesson.id == "abc"
    assert lesson.challenge_count == 2


def test_create_lesson_requires_id():
    with pytest.raises(Abort):
        create_lesson(FakeClient(session={"challenges": []}), Course("en", "es"))


def test_submit_lesson_reads_xp():
    lesson = create_lesson(FakeClient(), Course("en", "es"))
    result = submit_lesson(FakeClient(), lesson)
    assert result.lesson_id == "abc"
    assert result.xp_gain == 17


def test_submit_lesson_defaults_missing_xp_to_zero():
    lesson = create_lesson(FakeClient(), Course("en", "es"))
    result = submit_lesson(FakeClient(result={}), lesson)
    assert result.xp_gain == 0
