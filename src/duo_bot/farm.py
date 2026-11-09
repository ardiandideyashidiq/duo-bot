"""Bounded lesson loop used by both ``keep`` and ``farm``."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from .errors import Abort
from .sessions import Course, create_lesson, submit_lesson


@dataclass
class Stats:
    lessons: int = 0
    xp: int = 0
    failures: int = 0
    zero_xp_streak: int = 0
    interrupted: bool = False
    started: float = field(default_factory=time.monotonic)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started

    @property
    def xp_per_min(self) -> float:
        return self.xp / self.elapsed * 60 if self.elapsed > 0 else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "lessons": self.lessons,
            "xp": self.xp,
            "failures": self.failures,
            "elapsed_s": round(self.elapsed, 1),
            "xp_per_min": round(self.xp_per_min, 1),
            "interrupted": self.interrupted,
        }


def run_farm(
    client: Any,
    course: Course,
    *,
    target_xp: int = 100,
    max_lessons: int = 20,
    max_minutes: float = 15.0,
    delay: float = 1.0,
    jitter: float = 0.5,
    max_failures: int = 3,
    stop_after_zero: int = 3,
    dry_run: bool = False,
) -> Stats:
    """Run lessons until a cap is hit. Raises Abort on unrecoverable errors."""
    stats = Stats()

    while True:
        if stats.xp >= target_xp:
            logger.success("target reached: {} XP", stats.xp)
            break
        if stats.lessons >= max_lessons:
            logger.info("lesson cap reached ({})", stats.lessons)
            break
        if stats.elapsed >= max_minutes * 60:
            logger.info("time cap reached ({:.0f} min)", max_minutes)
            break

        stats.lessons += 1
        try:
            lesson = create_lesson(client, course)
            logger.debug("lesson {}: {} challenges", lesson.id, lesson.challenge_count)
            if dry_run:
                logger.warning("dry-run: session {} created but not submitted", lesson.id)
                gained = 0
            else:
                result = submit_lesson(client, lesson)
                gained = result.xp_gain
        except Abort:
            raise
        except KeyboardInterrupt:
            stats.interrupted = True
            logger.warning("interrupted")
            break
        except Exception as exc:  # noqa: BLE001 - transient network failures are expected
            stats.failures += 1
            logger.error("lesson {} failed: {}", stats.lessons, exc)
            if stats.failures >= max_failures:
                logger.error("too many failures ({}), stopping", stats.failures)
                break
            time.sleep(delay)
            continue

        stats.xp += gained
        if not dry_run:
            stats.zero_xp_streak = stats.zero_xp_streak + 1 if gained == 0 else 0

        eta = ""
        if target_xp > stats.xp and stats.xp_per_min > 0:
            eta = f" | eta {(target_xp - stats.xp) / stats.xp_per_min:.1f} min"
        logger.info(
            "lesson {:<3} +{:<3} XP | total {:<4} XP | {:.1f} XP/min{}",
            stats.lessons,
            gained,
            stats.xp,
            stats.xp_per_min,
            eta,
        )

        if not dry_run and stats.zero_xp_streak >= stop_after_zero:
            logger.warning(
                "{} sessions in a row gave 0 XP - daily practice cap likely reached",
                stats.zero_xp_streak,
            )
            break

        time.sleep(delay + random.uniform(0, jitter))

    return stats
