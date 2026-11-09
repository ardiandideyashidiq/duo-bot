"""Errors shared across duo-bot modules."""

from __future__ import annotations


class DuoBotError(Exception):
    """Base class for all duo-bot failures."""


class ConfigError(DuoBotError, ValueError):
    """Invalid or missing configuration (env vars, JWT, options)."""


class Abort(DuoBotError):
    """Unrecoverable API condition (bad response, exhausted retries)."""


class AuthError(Abort):
    """The Duolingo token is missing, expired, or rejected (HTTP 401/403)."""
