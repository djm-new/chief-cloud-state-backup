# OpenRouter spend attribution bug pattern

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
  - `weekly_transcript_chunk_extract`
  - `weekly_audio_script`
- `artifact`: output file path when there is one
- `run_id` or stable `backfill_key` for idempotent replay/backfill

## Important lessons

- Record the raw usage payload after normalizing it, because OpenRouter responses may arrive as dicts in raw HTTP scripts.
- If the helper calls `normalize_usage(...)`, make sure it converts raw dicts into an attribute-access object first; otherwise the ledger can silently record zero tokens/cost.
- Historical rows can need a one-time backfill from `raw_usage_json` if the recording shape changed.
- If historical artifacts already exist, backfill them once so the spend report reflects real usage immediately.

## Verification

- Spot-check the latest rows in `spend.db` for nonzero tokens and cost after a helper change.
- Confirm stage metadata is preserved so report rollups can break out semantic discovery vs scoring vs render.
- Run the helper against a known usage payload before relying on the cron report.
