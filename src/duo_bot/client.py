"""Thin Duolingo API client built on curl_cffi with Chrome impersonation."""

from __future__ import annotations

import time
from typing import Any

from curl_cffi.requests import RetryStrategy, Session
from loguru import logger

from .errors import Abort, AuthError

API_BASE = "https://www.duolingo.com/2017-06-30"
RETRY_STATUS = {429, 500, 502, 503, 504}


class DuolingoClient:
    """Synchronous API client. Use it as a context manager."""

    def __init__(
        self,
        token: str,
        *,
        impersonate: str = "chrome",
        timeout: float = 30.0,
        retries: int = 3,
    ) -> None:
        self._retries = retries
        self._session = Session(
            impersonate=impersonate,
            timeout=timeout,
            retry=RetryStrategy(count=2, delay=0.5, jitter=0.3, backoff="exponential"),
        )
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Origin": "https://www.duolingo.com",
                "Referer": "https://www.duolingo.com/",
            }
        )

    def __enter__(self) -> DuolingoClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._session.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        retries: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """Perform a JSON request, retrying 429/5xx and aborting on auth errors."""
        url = path if path.startswith("http") else f"{API_BASE}{path}"
        attempts = retries if retries is not None else self._retries

        for attempt in range(1, attempts + 1):
            resp = self._session.request(method, url, **kwargs)
            status = resp.status_code

            if status in (401, 403):
                raise AuthError(
                    f"{method} {path} -> HTTP {status}: token invalid/expired or blocked"
                )

            if status in RETRY_STATUS:
                if attempt == attempts:
                    raise Abort(f"{method} {path} kept returning HTTP {status}")
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else min(60.0, 2.0**attempt)
                except ValueError:
                    wait = min(60.0, 2.0**attempt)
                logger.warning(
                    "{} {} -> HTTP {} (attempt {}/{}), sleeping {:.1f}s",
                    method,
                    path,
                    status,
                    attempt,
                    attempts,
                    wait,
                )
                time.sleep(wait)
                continue

            if status >= 400:
                raise Abort(f"{method} {path} -> HTTP {status}: {resp.text[:300]}")

            try:
                return resp.json()
            except ValueError:
                raise Abort(f"{method} {path} returned non-JSON: {resp.text[:200]}") from None

        raise Abort(f"{method} {path}: retry loop exhausted")  # pragma: no cover

    def get_profile(self, sub: str, fields: str) -> dict[str, Any]:
        return self.request("GET", f"/users/{sub}", params={"fields": fields})

    def get_course(self, sub: str) -> tuple[str, str]:
        profile = self.get_profile(sub, "fromLanguage,learningLanguage")
        from_language = profile.get("fromLanguage")
        learning_language = profile.get("learningLanguage")
        if not (from_language and learning_language):
            raise Abort("profile response has no fromLanguage/learningLanguage")
        return from_language, learning_language

    def create_session(self, from_language: str, learning_language: str) -> dict[str, Any]:
        from .sessions import CHALLENGE_TYPES

        return self.request(
            "POST",
            "/sessions",
            json={
                "challengeTypes": CHALLENGE_TYPES,
                "fromLanguage": from_language,
                "isFinalLevel": False,
                "isV2": True,
                "juicy": True,
                "learningLanguage": learning_language,
                "smartTipsVersion": 2,
                "type": "GLOBAL_PRACTICE",
            },
        )

    def submit_session(
        self,
        session: dict[str, Any],
        *,
        elapsed: float = 60.0,
        hearts_left: int = 3,
        max_in_lesson_streak: int = 10,
        bonus_points: bool = True,
    ) -> dict[str, Any]:
        session_id = session.get("id")
        if not session_id:
            raise Abort(f"session response has no id: {list(session)[:10]}")
        now = time.time()
        return self.request(
            "PUT",
            f"/sessions/{session_id}",
            json={
                **session,
                "heartsLeft": hearts_left,
                "startTime": now - elapsed,
                "endTime": now,
                "enableBonusPoints": bonus_points,
                "failed": False,
                "maxInLessonStreak": max_in_lesson_streak,
                "shouldLearnThings": True,
            },
        )
