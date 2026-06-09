# Hermes spend reporting

This note captures the fix for daily/weekly spend briefing jobs.

## Root cause

A daily spend briefing originally used `agent.spend_ledger.summarize_spend(...)` over the raw `llm_usage_events` ledger. That path was useful for event-level attribution, but it underreported the full session-level spend picture the user expected.

## Correct reporting source

Use:
- `hermes_state.SessionDB`
- `agent.insights.InsightsEngine`

Why:
- `InsightsEngine.generate(days=N)` already computes:
  - `overview.estimated_cost`
  - `overview.actual_cost`
  - session counts
  - token counts
  - included/unknown pricing session counts
  - model/platform breakdowns
- It is the same source used by the built-in `hermes insights` command.

## Recommended daily report fields

- Estimated spend (last 24h)
- Actual billed spend (last 24h)
- Sessions (last 24h)
- Tokens (last 24h)
- Included sessions
- Unknown pricing sessions
- Top models
- Top platforms
- Project totals for the work done in the window
- Workflow/stage totals when available

## Recommended weekly report fields

- Estimated spend (last 7d)
- Actual billed spend (last 7d)
- Sessions (last 7d)
- Tokens (last 7d)
- Included sessions
- Unknown pricing sessions
- Top models
- Top platforms
- Project totals for the work done in the window
- Workflow/stage totals when available

## Verification

Useful local checks:

```bash
python3 -m hermes_cli.main insights --days 1
python3 -m hermes_cli.main spend summary --days 1 --by provider
```

The first command is the canonical report source for daily/weekly spend briefings.
The second command is useful for raw ledger comparison, but not as the primary user-facing spend report.
