# Daily health + spend wrapper pattern

Use this when a single Telegram delivery should combine the daily health check and the Hermes spend briefing.

## Why

- keeps the daily health update and spend snapshot in one scan-friendly message
- avoids a second separate spend notification when the spend section is only supporting context
- preserves the health check's actionable tone while still surfacing spend
- stays robust across ET/DST by using a date guard in the wrapper, not in cron alone

## Pattern

1. Run the health check first with forced reporting enabled.
2. Run the spend briefing next with forced reporting enabled.
3. Print the health section before the spend section.
4. Keep the wrapper script idempotent for the ET day.
5. Make the cron job `no_agent: true` so the wrapper output is the delivery.

## Environment flags used

- `CHIEF_HEALTH_ALWAYS_REPORT=1`
- `HERMES_SPEND_REPORT_FORCE=1`
- optional wrapper-only guard like `HERMES_DAILY_HEALTH_SPEND_FORCE=1` for debugging

## Practical notes

- Use a separate state file under `/opt/data/spend-monitor/` or similar for the ET-date dedupe key.
- Do not rely on raw cron timing alone for 5AM ET jobs; use UTC candidate wakeups plus an in-script ET hour/date check.
- Keep the wrapper lightweight: shell/Python orchestration only, no LLM turn unless the job is actually a summary job that needs it.
- If the combined output is meant for Telegram, make it self-identifying and concise; avoid wrapper boilerplate and job metadata.

## Example sequence

```text
Health check
  -> spend briefing
  -> one Telegram message
```

## Verification

- run the wrapper once with its force flag
- confirm the health section renders first
- confirm the spend section includes the expected 24h and 7d windows
- confirm the cron job is scheduled as a single delivery, not two separate jobs
