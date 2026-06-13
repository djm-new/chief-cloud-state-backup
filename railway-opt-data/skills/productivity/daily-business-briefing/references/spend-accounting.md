# Spend accounting for briefing workflows

This workflow can generate authoritative usage in the session/state DB even when `llm_usage_events` is incomplete or sparse.

## Rule

- Treat briefing session rows as real LLM usage when they contain token/cost fields.
- Merge session rows with spend-event rows for reporting.
- Deduplicate by `session_id` when both sources refer to the same run.

## Practical implication

A zero-value spend-event row does **not** mean the briefing was non-LLM. For daily briefing and related synthesis jobs, check the session record before concluding that no model usage occurred.

## Debugging cue

If the headline spend summary is lower than expected, compare:

- `spend.db` → event rows
- `state.db` → session rows

The session DB may contain the missing tokens/costs.
