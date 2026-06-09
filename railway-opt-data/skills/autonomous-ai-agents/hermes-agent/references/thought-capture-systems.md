# Thought capture systems inside Hermes

Use this when building a dedicated low-friction capture channel (Telegram/Slack/etc.) that writes local markdown artifacts and runs scheduled synthesis.

## Durable architecture pattern

- Storage: local-first git repo under `$HERMES_HOME`/persistent volume with plain markdown (`daily/`, `weekly/`, `monthly/`, `quarterly/`, `attachments/`, `prompts/`, `config/`).
- Privacy: write the local/encrypted/private-remote decision in `README.md` before the first commit.
- Capture: append-only daily files; never rewrite historical entries. Corrections are new entries (`correction:`), not edits.
- Intensity: a leading `!` should be carried into storage and ranking/synthesis as a weight signal only, not a tag/category.
- Voice: preserve original audio under `attachments/YYYY/MM/DD/`; pass `config/vocab.txt` to Whisper `initial_prompt`; run `config/corrections.json` regex cleanup after transcription.
- URLs/images: preserve source artifacts where possible; append extracted/summarized text with explicit markers (`[link]`, `[image]`).
- Retrieval: return underlying excerpts with date/time/context even when offering synthesis; rank exact matches before intensity flags before semantic matches.

## Hermes integration pattern

- Put reusable logic in a standalone script (e.g. `thoughts_system.py`) with subcommands for `init`, `capture`, `rollup`, `replay`, `synthesize`, and `retrieve`.
- Add a small gateway hook module that checks a config section such as:

```yaml
thoughts:
  enabled: true
  repo_path: /opt/data/thoughts-repo
  timezone: America/New_York
  telegram:
    chat_id: '-100...'
    thread_id: '6'
```

- Hook early in `BasePlatformAdapter.handle_message()` before normal session locking/LLM dispatch. Return `(handled, response)` semantics: captures are silent on success; retrieval-style questions return excerpts.
- For command-like requests in the thought-capture topic, parse and handle them before generic capture. Example: Daily ToM quick-add phrases such as `add to top of mind "XM comp check"`, `add "XM comp check" to top of mind`, or `tom: XM comp check` should call a deterministic Google Docs updater and return a confirmation, not fall through to ordinary thought capture. Keep parsers conservative and exact-prefix based so normal thoughts are not accidentally converted into commands.
- Match by platform + chat_id + optional thread/topic id. For Telegram forum topics, delivery/capture targets use `telegram:<chat_id>:<message_thread_id>` and `SessionSource.thread_id`.
- Restart the gateway after code-hook changes; config-only changes generally still need gateway reload/restart if the module/config is already loaded. In Railway/container gateways where PID 1 is the gateway, CLI `hermes gateway restart` may not replace the live process cleanly; report code/config as staged until the container/gateway is restarted or a verified replacement run is active.

## Cron pattern

- Cron tool script paths must be relative script names in the Hermes scripts directory; absolute paths are rejected. Keep the implementation script there or wrap it with a thin script there.
- Cron schedules are interpreted by the scheduler in UTC. For America/New_York wall-clock jobs that must survive DST, schedule both possible UTC hours and add a local-time guard inside the script:
  - 00:05 ET -> `5 4,5 * * *`, guard `hour == 0 and minute == 5` in `ZoneInfo('America/New_York')`.
  - 07:00 ET -> `0 11,12 * * *`, guard `hour == 7`.
  - 05:30 Monday ET -> `30 9,10 * * 1`, guard weekday/hour/minute.
  - 09:00 ET -> `0 13,14 ...`, guard hour 9.
- Script-only jobs should be silent on success and emit actionable failure text only, unless the job's purpose is delivery (e.g. morning replay/synthesis).

## Monthly/quarterly delivery artifacts

For monthly and quarterly syntheses, prefer delivering the generated `.md`/`.txt` artifact directly instead of long inline previews or email. In Telegram delivery scripts, emit a short status line plus `MEDIA:/absolute/path/to/file` so the gateway sends the markdown/text as an attachment. Weekly syntheses can remain inline when concise.

## Google/calendar safety

If creating review calendar blocks from synthesis output, create events without attendees and without notification-triggering actions unless the user explicitly changes their policy. For DJ's environment, use the local `google-account personal ...` wrapper when available; it blocks attendee invites by policy. If Calendar behavior is not currently the focus, gate quarterly calendar creation behind an explicit opt-in env var (for example `THOUGHTS_ENABLE_CALENDAR=1`) rather than letting synthesis jobs touch Calendar by default.

## Private GitHub remote pattern

When DJ approves GitHub for a local thought-capture repo, use a private GitHub remote only. If GitHub auth is not already available, add a checked-in setup helper under the repo (for example `scripts/setup_github_remote.py`) that requires `GITHUB_TOKEN`/`GH_TOKEN` with `repo` scope at runtime, creates or reuses the private repo, sets `origin`, pushes the local branch to `main`, and never prints the token. Document the private-remote decision and setup command in `README.md`. Do not auto-run the helper from cron or synthesis jobs.

If the goal is to preserve conversation history for cloud backup, export a redacted session corpus into the thought repo before syncing (for example `exports/sessions-redacted/` plus an index file). Keep raw session JSON local; GitHub should receive the redacted derivative, not the secret-bearing source files.

## Model/provider verification pitfall

Changing `model.provider`/`model.default` in Hermes config is not the same as verifying the provider can run. When switching a job/system to OpenAI, run a tiny `hermes chat -q ... --provider openai --model <model>` smoke test. If it falls back because auth is missing, report that config is changed but OpenAI execution is blocked until `OPENAI_API_KEY` is configured.

## Verification checklist

1. Initialize repo and confirm `README.md` privacy section exists before first commit.
2. Smoke test text capture writes the correct daily path and creates a git commit.
3. Smoke test retrieval returns date/time/context excerpts.
4. Py-compile any gateway hook and scripts.
5. Simulate a platform `MessageEvent` to confirm the dedicated channel is handled and non-matching channels pass through.
6. List cron jobs and verify delivery target/topic and next run times.
7. Confirm gateway restart/reload status before telling the user the live capture path is active.