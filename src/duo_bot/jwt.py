"""JWT helpers: decode the payload and redact secrets from text."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

from .errors import ConfigError

_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_TELEGRAM_TOKEN_RE = re.compile(r"\bbot\d+:[A-Za-z0-9_-]{20,}\b")


def decode_claims(token: str) -> dict[str, Any]:
    """Decode the JWT payload **without** verifying the signature."""
    parts = token.split(".")
    if len(parts) < 2:
        raise ConfigError("DUOLINGO_JWT is not a JWT (missing payload segment)")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot decode JWT payload: {exc}") from None
    if not isinstance(claims, dict):
        raise ConfigError("JWT payload is not a JSON object")
    return claims


def get_subject(token: str) -> str:
    sub = decode_claims(token).get("sub")
    if not sub:
        raise ConfigError("no `sub` claim in DUOLINGO_JWT")
    return str(sub)


def mask_id(value: str) -> str:
    """Show only the last 4 characters of an identifier."""
    text = str(value)
    return f"{'*' * max(0, len(text) - 4)}{text[-4:]}"


def redact(text: str) -> str:
    """Remove bearer tokens, JWTs and Telegram bot tokens from a string."""
    text = _BEARER_RE.sub("Bearer ***", text)
    text = _JWT_RE.sub("***", text)
    return _TELEGRAM_TOKEN_RE.sub("bot***", text)
