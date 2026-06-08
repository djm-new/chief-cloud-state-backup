# Podcast OpenRouter spend attribution

This podcast pipeline uses OpenRouter directly from script-level calls, so the Hermes agent loop never sees the usage unless the scripts explicitly record it.

## What to record

For each OpenRouter call, capture:

- `project_slug`: `podcast-intelligence-digest`
- `source`: `cron`
- `platform`: `cron`
- `workflow`: `podcast-intelligence-digest`
- `stage`: one of:
  - `semantic_query_generation`
  - `semantic_candidate_filter`
  - `episode_scoring`
  - `daily_digest_render`
- `artifact`: output file path when there is one
- `run_id` or stable `backfill_key` for idempotent replay/backfill

## Important

- Use Hermes spend ledger recording, not ad hoc notes in the output artifact.
- Record the raw usage payload after normalizing it, because OpenRouter responses may arrive as dicts in raw HTTP scripts.
- If historical artifacts already exist, backfill them once so the spend report reflects real usage immediately.
