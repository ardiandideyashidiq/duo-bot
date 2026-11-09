# duo-bot

Keep Duolingo streaks alive and farm XP via `curl-cffi` (Chrome TLS impersonation) and GitHub Actions. Submits `GLOBAL_PRACTICE` sessions only.

## Quickstart

```bash
uv sync
cp .env.example .env  # set DUOLINGO_JWT
uv run duo-bot status
uv run duo-bot keep   # extends streak if not done today
uv run duo-bot farm --target-xp 100 --max-lessons 20
```

Extract `DUOLINGO_JWT` from browser console while logged into Duolingo:
```js
document.cookie.split("; ").find(c => c.startsWith("jwt_token=")).split("=")[1]
```

### Environment (`.env`)

```bash
DUOLINGO_JWT="..."
TZ="Asia/Jakarta"          # optional (default: account tz or UTC)
TELEGRAM_BOT_TOKEN="..."   # optional
TELEGRAM_CHAT_ID="..."     # optional
```

## Commands

- `duo-bot keep [--force] [--dry-run]`: Idempotent daily streak extension.
- `duo-bot farm [--target-xp N] [--max-lessons N] [--dry-run]`: Bounded XP loop.
- `duo-bot status [--json]`: Show account streak, total XP, and timezone.
- `duo-bot notify --status <status>`: Send Telegram notification.

Flags: `--env PATH`, `--log-file PATH`, `--log-level`, `--tz`, `--impersonate`, `--timeout`. Logs rotate at `logs/duo-bot.log` with secrets redacted.

## GitHub Actions

Set repository secret `DUOLINGO_JWT` (and optionally `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`):

- **`streak.yml`**: Scheduled at 02:00 & 14:00 Asia/Jakarta (`0 19 * * *`, `0 7 * * *` UTC) + manual trigger.
- **`farm.yml`**: Manual trigger (`target_xp`, `max_lessons`, `dry_run`).
- **`ci.yml`**: Ruff lint/format check + pytest suite.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```
