# Direct OpenRouter HTTP spend capture

Use this when Hermes-owned scripts call OpenRouter directly via `requests.post(...)` or another raw HTTP client instead of going through the Hermes agent loop.

## Problem pattern

A script can successfully generate and render outputs, but the central Hermes spend ledger stays blind if the script never passes through the agent response-usage hook.

That creates the illusion that Hermes spent nothing on the workflow even though the workflow was actively directed by Hermes and used OpenRouter models.

## Fix pattern

1. **Normalize the raw usage payload** with `agent.usage_pricing.normalize_usage(...)`.
2. **Estimate cost** with `agent.usage_pricing.estimate_usage_cost(...)`.
3. **Record a spend event** with `agent.spend_ledger.record_spend_event(...)`.
4. Set a stable `project_slug`, `source`, `platform`, and `metadata.stage` so the ledger can group by project/channel/source later.
5. Backfill from saved artifacts if the workflow already produced outputs before the ledger fix.

## Important compatibility note

OpenRouter and other proxies may return **dict-shaped usage payloads** from raw HTTP responses. Ensure the normalizer accepts both:

- attribute-style objects, and
- plain dicts

If dict payloads are passed through `normalize_usage()` without dict access support, token counts can silently collapse to zero in the spend ledger.

## Good metadata fields for direct scripts

- `workflow`: human-readable umbrella name, e.g. `podcast-intelligence-digest`
- `stage`: sub-step, e.g. `semantic_query_generation`, `episode_scoring`, `daily_digest_render`
- `artifact`: file path to the generated output, if applicable
- `backfill_key`: unique id for idempotent replays/backfills
- `run_id`: semantic-discovery or batch run identifier

## Verification

After patching a workflow:

- run the workflow once,
- check `hermes spend project --days 30` or equivalent summary,
- confirm the workflow now appears under the intended project label,
- confirm token totals are non-zero and grouped under the right provider.
