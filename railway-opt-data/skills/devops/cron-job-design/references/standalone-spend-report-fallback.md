# Standalone spend briefing fallback

## When to use

Use this pattern when a cron-delivered spend briefing script is meant to run outside the Hermes app/runtime and cannot rely on `agent.*` or `hermes_constants` being importable.

## What the fix looked like (2026-07: superseded by unified helper)

- The shared helper is `/opt/data/scripts/spend_report_helper.py`.
- **2026-07 rebuild:** the helper no longer chooses between "Hermes path OR
  spend.db". It always builds a unified report from direct SQLite reads —
  `state.db` sessions (primary) + `spend.db` events (deduped by session_id) —
  so it behaves identically under the venv python and the stripped-down cron
  python. Hermes imports (`agent.usage_pricing`) are used opportunistically
  for pricing only, with a direct OpenRouter HTTP fallback. See
  `references/unified-spend-reporting.md` for the full architecture.
- Resolve `HERMES_HOME` locally with `os.getenv("HERMES_HOME")` or `Path.home() / ".hermes"` instead of importing `hermes_constants`.

## Why this mattered

A cron script that imported `agent.spend_ledger` directly crashed before rendering because the cron Python environment did not have Hermes modules on `sys.path`. The fallback helper kept the briefing alive while preserving the richer session-insights path when available.

## Verification

- Run the script with the forced-report flag.
- Confirm it emits a full briefing instead of a traceback.
- Compile the helper and both briefing scripts with `py_compile`.
