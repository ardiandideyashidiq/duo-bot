"""Environment loading and typed helpers."""

from __future__ import annotations

import os
import time
from pathlib import Path

from .errors import ConfigError

DEFAULT_ENV_FILE = Path(".env")


def load_env(path: Path | str = DEFAULT_ENV_FILE, *, override: bool = False) -> None:
    """Load a minimal ``.env`` file into ``os.environ``.

    Supports ``KEY=VALUE``, ``export KEY=VALUE``, single/double quotes and
    trailing ``# comments``. Existing variables win unless ``override=True``.
    """
    path = Path(path)
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if override or key not in os.environ:
            os.environ[key] = value


def get(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def get_int(name: str, default: int) -> int:
    raw = get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from None


def get_float(name: str, default: float) -> float:
    raw = get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from None


def get_bool(name: str, default: bool = False) -> bool:
    raw = get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def configure_timezone(tz: str | None = None) -> str:
    """Apply a timezone to the process (Linux ``TZ`` + ``tzset``)."""
    resolved = tz or get("TZ") or "UTC"
    os.environ["TZ"] = resolved
    if hasattr(time, "tzset"):
        time.tzset()
    return resolved


def require_token() -> str:
    token = get("DUOLINGO_JWT")
    if not token:
        raise ConfigError("DUOLINGO_JWT is missing (set it in .env or the environment)")
    return token.strip()
