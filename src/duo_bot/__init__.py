"""duo-bot command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from .client import DuolingoClient
from .config import configure_timezone, load_env, require_token
from .errors import DuoBotError
from .farm import run_farm
from .jwt import get_subject, mask_id
from .keep import run_keep
from .logging import DEFAULT_LOG_FILE, setup_logging, summary_table, write_step_summary
from .notify import notify as _notify
from .notify import tail_log
from .sessions import Course

EXIT_OK = 0
EXIT_FAIL = 1


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env", type=Path, default=Path(".env"), help="path to the .env file")
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG_FILE)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--tz", default=None, help="process timezone (default: $TZ or UTC)")


def _add_network(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--impersonate", default="chrome", help="curl_cffi browser target")
    parser.add_argument("--timeout", type=float, default=30.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="duo-bot", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    keep = sub.add_parser("keep", help="extend today's streak once (idempotent)")
    _add_common(keep)
    _add_network(keep)
    keep.add_argument("--lessons", type=int, default=1)
    keep.add_argument("--force", action="store_true", help="run even if already extended today")
    keep.add_argument("--dry-run", action="store_true")

    farm = sub.add_parser("farm", help="farm XP with bounded loops")
    _add_common(farm)
    _add_network(farm)
    farm.add_argument("--target-xp", type=int, default=100)
    farm.add_argument("--max-lessons", type=int, default=20)
    farm.add_argument("--max-minutes", type=float, default=15.0)
    farm.add_argument("--delay", type=float, default=1.0)
    farm.add_argument("--jitter", type=float, default=0.5)
    farm.add_argument("--max-failures", type=int, default=3)
    farm.add_argument("--stop-after-zero", type=int, default=3)
    farm.add_argument("--dry-run", action="store_true")

    status = sub.add_parser("status", help="read-only streak/token status")
    _add_common(status)
    _add_network(status)
    status.add_argument("--json", action="store_true")

    notify_cmd = sub.add_parser("notify", help="send the optional Telegram notification")
    _add_common(notify_cmd)
    notify_cmd.add_argument("--status", default="failure", help="success|failure|cancelled")
    notify_cmd.add_argument("--summary-file", type=Path, default=None)
    notify_cmd.add_argument("--title", default="duo-bot")
    return parser


def _client(args: argparse.Namespace) -> DuolingoClient:
    return DuolingoClient(require_token(), impersonate=args.impersonate, timeout=args.timeout)


def _cmd_keep(args: argparse.Namespace) -> int:
    token = require_token()
    sub = get_subject(token)
    logger.info("user: {}", mask_id(sub))

    with _client(args) as client:
        result = run_keep(
            client,
            sub,
            lessons=args.lessons,
            force=args.force,
            dry_run=args.dry_run,
            tz=args.tz,
        )

    stats = result.stats
    rows: dict[str, Any] = {
        "status": "ok" if result.ran else "skipped",
        "reason": result.reason,
        "timezone": result.timezone,
        "last_extended": result.last_extended or "-",
    }
    if stats:
        rows.update(stats.as_dict())
    write_step_summary(summary_table("duo-bot keep", rows))

    if stats:
        logger.success(
            "keep done: {} lessons, {} XP in {:.1f}s",
            stats.lessons,
            stats.xp,
            stats.elapsed,
        )
    return EXIT_OK


def _cmd_farm(args: argparse.Namespace) -> int:
    token = require_token()
    sub = get_subject(token)
    logger.info("user: {}", mask_id(sub))

    with _client(args) as client:
        profile = client.get_profile(sub, "fromLanguage,learningLanguage")
        course = Course.from_profile(profile)
        logger.info("course: {} -> {}", course.from_language, course.learning_language)
        stats = run_farm(
            client,
            course,
            target_xp=args.target_xp,
            max_lessons=args.max_lessons,
            max_minutes=args.max_minutes,
            delay=args.delay,
            jitter=args.jitter,
            max_failures=args.max_failures,
            stop_after_zero=args.stop_after_zero,
            dry_run=args.dry_run,
        )

    rows = {"status": "dry-run" if args.dry_run else "ok", **stats.as_dict()}
    write_step_summary(summary_table("duo-bot farm", rows))
    logger.success(
        "farm done: {} lessons, {} XP in {:.1f}s ({:.1f} XP/min), {} failures",
        stats.lessons,
        stats.xp,
        stats.elapsed,
        stats.xp_per_min,
        stats.failures,
    )
    return EXIT_OK


def _cmd_status(args: argparse.Namespace) -> int:
    token = require_token()
    sub = get_subject(token)
    with _client(args) as client:
        profile = client.get_profile(
            sub, "fromLanguage,learningLanguage,streak,streakData,totalXp,timezone"
        )

    last_extended = ((profile.get("streakData") or {}).get("currentStreak") or {}).get(
        "lastExtendedDate"
    )
    rows: dict[str, Any] = {
        "user": mask_id(sub),
        "course": f"{profile.get('fromLanguage')} -> {profile.get('learningLanguage')}",
        "streak": profile.get("streak"),
        "totalXp": profile.get("totalXp"),
        "lastExtendedDate": last_extended,
        "timezone": profile.get("timezone"),
    }
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for key, value in rows.items():
            logger.info("{}: {}", key, value)
    write_step_summary(summary_table("duo-bot status", rows))
    return EXIT_OK


def _cmd_notify(args: argparse.Namespace) -> int:
    summary = ""
    if args.summary_file and args.summary_file.is_file():
        summary = args.summary_file.read_text(encoding="utf-8")
    if not summary:
        summary = tail_log(args.log_file)
    _notify(args.status, summary=summary, title=args.title)
    # A failed notification must never turn a successful job red.
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_timezone(getattr(args, "tz", None))
    setup_logging(
        level=getattr(args, "log_level", "INFO"),
        log_file=getattr(args, "log_file", DEFAULT_LOG_FILE),
    )

    try:
        load_env(getattr(args, "env", Path(".env")))
        command = {
            "keep": _cmd_keep,
            "farm": _cmd_farm,
            "status": _cmd_status,
            "notify": _cmd_notify,
        }[args.command]
        return command(args)
    except KeyboardInterrupt:
        logger.warning("interrupted")
        return 130
    except DuoBotError as exc:
        logger.error("{}", exc)
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
