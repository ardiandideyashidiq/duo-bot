"""Idempotent streak keeper: one lesson per day, in the account's timezone."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from loguru import logger

from .farm import Stats, run_farm
from .sessions import Course

PROFILE_FIELDS = "fromLanguage,learningLanguage,streak,streakData,totalXp,timezone"


@dataclass(frozen=True)
class KeepResult:
    ran: bool
    reason: str
    timezone: str
    last_extended: str | None
    stats: Stats | None = None


def account_today(timezone: str, now: datetime | None = None) -> str:
    """Return today's date (YYYY-MM-DD) in the account timezone."""
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError, ValueError:
        logger.warning("unknown timezone {!r}, falling back to UTC", timezone)
        zone = ZoneInfo("UTC")
    current = now.astimezone(zone) if now else datetime.now(zone)
    return current.date().isoformat()


def run_keep(
    client: Any,
    sub: str,
    *,
    lessons: int = 1,
    force: bool = False,
    dry_run: bool = False,
    tz: str | None = None,
    now: datetime | None = None,
    **farm_kwargs: Any,
) -> KeepResult:
    profile = client.get_profile(sub, PROFILE_FIELDS)
    timezone = tz or profile.get("timezone") or os.environ.get("TZ") or "UTC"
    today = account_today(timezone, now=now)
    last_extended = ((profile.get("streakData") or {}).get("currentStreak") or {}).get(
        "lastExtendedDate"
    )

    if not force and last_extended == today:
        logger.info("streak already extended today ({} in {})", today, timezone)
        return KeepResult(
            ran=False,
            reason=f"already extended today ({today} {timezone})",
            timezone=timezone,
            last_extended=last_extended,
        )

    course = Course.from_profile(profile)
    logger.info(
        "course: {} -> {} | timezone: {}", course.from_language, course.learning_language, timezone
    )
    stats = run_farm(
        client,
        course,
        target_xp=10**9,
        max_lessons=lessons,
        max_minutes=farm_kwargs.pop("max_minutes", 5.0),
        dry_run=dry_run,
        **farm_kwargs,
    )
    return KeepResult(
        ran=True,
        reason="extended",
        timezone=timezone,
        last_extended=last_extended,
        stats=stats,
    )
