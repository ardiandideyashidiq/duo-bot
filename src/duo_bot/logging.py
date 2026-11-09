"""Loguru setup with secret redaction and GitHub step summaries."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from .jwt import redact

DEFAULT_LOG_FILE = Path("logs/duo-bot.log")
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"


def _redact_record(record: dict[str, Any]) -> None:
    record["message"] = redact(str(record["message"]))


def setup_logging(
    *,
    level: str = "INFO",
    log_file: Path | str | None = DEFAULT_LOG_FILE,
    console: bool = True,
) -> None:
    """Configure stderr logging plus (optionally) a rotating file."""
    logger.remove()
    logger.configure(patcher=_redact_record)

    if console:
        logger.add(sys.stderr, level=level, format=LOG_FORMAT)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            path,
            level=level,
            format=LOG_FORMAT,
            rotation="5 MB",
            retention="7 days",
            encoding="utf-8",
        )
        logger.debug("logging to {}", path)


def write_step_summary(markdown: str) -> bool:
    """Append markdown to ``$GITHUB_STEP_SUMMARY`` when running in Actions."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return False
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(markdown.rstrip() + "\n")
    return True


def summary_table(title: str, rows: dict[str, Any]) -> str:
    lines = [f"### {title}", "", "| field | value |", "| --- | --- |"]
    lines.extend(f"| {key} | {value} |" for key, value in rows.items())
    return "\n".join(lines) + "\n"
