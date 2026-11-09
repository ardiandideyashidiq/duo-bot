"""Session/course value objects and the create/submit steps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .errors import Abort

CHALLENGE_TYPES = [
    "assist",
    "characterIntro",
    "characterMatch",
    "characterPuzzle",
    "characterSelect",
    "characterTrace",
    "characterWrite",
    "completeReverseTranslation",
    "definition",
    "dialogue",
    "extendedMatch",
    "extendedListenMatch",
    "form",
    "freeResponse",
    "gapFill",
    "judge",
    "listen",
    "listenComplete",
    "listenMatch",
    "match",
    "name",
    "listenComprehension",
    "listenIsolation",
    "listenSpeak",
    "listenTap",
    "orderTapComplete",
    "partialListen",
    "partialReverseTranslate",
    "patternTapComplete",
    "radioBinary",
    "radioImageSelect",
    "radioListenMatch",
    "radioListenRecognize",
    "radioSelect",
    "readComprehension",
    "reverseAssist",
    "sameDifferent",
    "select",
    "selectPronunciation",
    "selectTranscription",
    "svgPuzzle",
    "syllableTap",
    "syllableListenTap",
    "speak",
    "tapCloze",
    "tapClozeTable",
    "tapComplete",
    "tapCompleteTable",
    "tapDescribe",
    "translate",
    "transliterate",
    "transliterationAssist",
    "typeCloze",
    "typeClozeTable",
    "typeComplete",
    "typeCompleteTable",
    "writeComprehension",
]


class LessonClient(Protocol):
    def create_session(self, from_language: str, learning_language: str) -> dict[str, Any]: ...

    def submit_session(self, session: dict[str, Any], **kwargs: Any) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Course:
    from_language: str
    learning_language: str

    @classmethod
    def from_profile(cls, profile: dict[str, Any]) -> Course:
        from_language = profile.get("fromLanguage")
        learning_language = profile.get("learningLanguage")
        if not (from_language and learning_language):
            raise Abort("profile response has no fromLanguage/learningLanguage")
        return cls(from_language=from_language, learning_language=learning_language)


@dataclass(frozen=True)
class Lesson:
    id: str
    challenge_count: int
    raw: dict[str, Any]


@dataclass(frozen=True)
class LessonResult:
    lesson_id: str
    xp_gain: int
    raw: dict[str, Any]


def create_lesson(client: LessonClient, course: Course) -> Lesson:
    raw = client.create_session(course.from_language, course.learning_language)
    session_id = raw.get("id")
    if not session_id:
        raise Abort(f"session response has no id: {list(raw)[:10]}")
    return Lesson(
        id=str(session_id),
        challenge_count=len(raw.get("challenges") or []),
        raw=raw,
    )


def submit_lesson(client: LessonClient, lesson: Lesson, **kwargs: Any) -> LessonResult:
    raw = client.submit_session(lesson.raw, **kwargs)
    raw.setdefault("id", lesson.id)
    try:
        xp_gain = int(raw.get("xpGain") or 0)
    except TypeError, ValueError:
        xp_gain = 0
    return LessonResult(lesson_id=lesson.id, xp_gain=xp_gain, raw=raw)
