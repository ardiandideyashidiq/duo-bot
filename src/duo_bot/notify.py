"""Optional Telegram notifications (no-op when secrets are absent)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from curl_cffi import requests
from loguru import logger

from .config import get
from .jwt import redact

TELEGRAM_LIMIT = 4096


def build_message(status: str, summary: str | None = None, *, title: str = "duo-bot") -> str:
    icon = "✅" if status.lower() == "success" else "🔴"
    lines = [f"{icon} {title}: {status}"]
    if summary:
        body = redact(summary.strip())
        room = TELEGRAM_LIMIT - len("\n".join(lines)) - 2
        lines.extend(["", body[:room]])
    return "\n".join(lines)


def tail_log(path: Path | str, lines: int = 8) -> str:
    path = Path(path)
    if not path.is_file():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def send_telegram(
    text: str,
    *,
    token: str | None = None,
    chat_id: str | None = None,
    timeout: float = 10.0,
    retries: int = 2,
) -> bool:
    token = (token or get("TELEGRAM_BOT_TOKEN") or "").strip().strip("'\"")
    chat_id = (chat_id or get("TELEGRAM_CHAT_ID") or "").strip().strip("'\"")
    if not (token and chat_id):
        logger.info("telegram is not configured; skipping notification")
        return False

    # The bot token is part of the URL: never log the URL itself.
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    for attempt in range(1, retries + 2):
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - notification must never crash the job
            logger.warning("telegram request failed (attempt {}): {}", attempt, type(exc).__name__)
        else:
            desc = ""
            try:
                data = resp.json()
                ok = resp.status_code == 200 and bool(data.get("ok"))
                desc = str(data.get("description") or getattr(resp, "text", ""))
            except ValueError:
                ok = resp.status_code == 200
                desc = getattr(resp, "text", "")

            if ok:
                logger.info("telegram notification sent")
                return True

            detail = f": {redact(desc.strip())}" if desc else ""
            logger.warning("telegram returned HTTP {}{}", resp.status_code, detail)
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                return False
        if attempt <= retries:
            time.sleep(min(5.0, 2.0**attempt))
    return False


def notify(
    status: str,
    *,
    summary: str | None = None,
    title: str = "duo-bot",
) -> bool:
    return send_telegram(build_message(status, summary, title=title))
