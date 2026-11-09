# duo-bot

Keep a Duolingo streak alive and optionally farm XP, driven by `curl-cffi`
(Chrome TLS impersonation) and GitHub Actions.

> **Disclaimer:** automating Duolingo sessions violates Duolingo's Terms of
> Service. Use it on your own account, at your own risk. The bot never answers
> real lessons; it only submits `GLOBAL_PRACTICE` sessions, so it does not
> advance your learning path (and does not complete daily/friend quests).

## How it works

1. Decode the `sub` claim from `DUOLINGO_JWT` (no signature verification).
2. `GET /2017-06-30/users/{sub}` to read the course and streak.
3. `POST /2017-06-30/sessions` to create a `GLOBAL_PRACTICE` session.
4. `PUT /2017-06-30/sessions/{id}` with the session echoed back and
   `startTime = now - 60s`, `endTime = now`, `failed = false`, which the server
   accepts as a completed lesson and pays XP for.

## Local usage

```bash
uv sync
cp .env.example .env        # then fill DUOLINGO_JWT
uv run duo-bot status
uv run duo-bot keep --dry-run
uv run duo-bot keep
uv run duo-bot farm --target-xp 100 --max-lessons 20
```

Get the JWT from the browser while logged into Duolingo:

```js
document.cookie
  .split(";")
  .find((cookie) => cookie.includes("jwt_token"))
  .split("=")[1];
```

`.env`:

```bash
DUOLINGO_JWT="your.jwt.token"
TZ=Asia/Jakarta
```

Optional Telegram notifications:

```bash
TELEGRAM_BOT_TOKEN="123456:ABC..."
TELEGRAM_CHAT_ID="123456789"
TELEGRAM_NOTIFY="failure"   # failure (default) | success | all | success,failure
```

## Commands

| Command | Purpose |
| --- | --- |
| `duo-bot keep` | Extend today's streak once. Skips when `lastExtendedDate` is already today in the account timezone (`--force` overrides). |
| `duo-bot farm` | Bounded XP loop with retry, 0-XP cap detection and `--dry-run`. |
| `duo-bot status` | Read-only streak/token check (`--json` for scripting). |
| `duo-bot notify` | Send the optional Telegram message for a job status. |

Global flags: `--env PATH`, `--log-file PATH`, `--log-level`, `--tz`.
Network flags: `--impersonate chrome`, `--timeout 30`.

Logs are written to `logs/duo-bot.log` (rotated at 5 MB, kept 7 days) and
redacted: bearer tokens, JWTs and Telegram bot tokens never reach the log.

## GitHub Actions

The repository ships three workflows:

| Workflow | Trigger | Notes |
| --- | --- | --- |
| `ci.yml` | push / PR | ruff + pytest, no network |
| `streak.yml` | `0 19 * * *` and `0 7 * * *` (UTC) | **02:00 and 14:00 Asia/Jakarta**; `keep` is idempotent, so the second run is a safety net |
| `farm.yml` | `workflow_dispatch` only | manual form: `target_xp`, `max_lessons`, `dry_run` |

Setup:

1. Fork/push this repository.
2. Add repository secret `DUOLINGO_JWT` (Settings → Secrets and variables → Actions).
3. Optional secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and variable
   `TELEGRAM_NOTIFY` (`failure`, `success`, `all`).
4. Enable workflows in the Actions tab and run `duo-bot keep streak` once via
   **Run workflow** to verify.

Caching is minimal: `astral-sh/setup-uv` caches the uv wheel cache keyed on
`uv.lock` and, with `cache-python: true`, the managed Python 3.15 install. The
virtualenv and any XP state are deliberately not cached — each run is stateless
and `$GITHUB_STEP_SUMMARY` plus a short-lived log artifact provide visibility.

### Timezone notes

GitHub cron schedules are **UTC**. `02:00` and `14:00` in `Asia/Jakarta`
(UTC+7) are `19:00` and `07:00` UTC. The workflow sets `TZ=Asia/Jakarta`, and
`keep` additionally uses the account's own `timezone` field from the API, so
the "already extended today" check stays correct regardless of the runner.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Integration tests against the real API are intentionally excluded from CI:

```bash
DUOLINGO_JWT=... uv run pytest -m integration
```
