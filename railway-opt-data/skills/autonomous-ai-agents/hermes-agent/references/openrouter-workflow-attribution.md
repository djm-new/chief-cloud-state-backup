# OpenRouter workflow attribution for Hermes-owned scripts

Use this pattern when a Hermes-owned script talks to OpenRouter directly instead of going through the normal agent loop.

## Why

Provider totals alone are not enough. DJ needs answers like:

- which project used the tokens?
- which workflow/stage used them?
- which model carried the cost?

## Required fields

When recording usage from a raw OpenRouter response, include:

- `project_slug`: stable project name, e.g. `podcast-intelligence-digest`
- `source`: where the call came from, e.g. `cron`, `cli`, `gateway`
- `platform`: same as source unless you need a finer distinction
- `metadata.workflow`: umbrella workflow name, e.g. `podcast-intelligence-digest`
- `metadata.stage`: step name, e.g. `semantic_query_generation`, `episode_scoring`, `daily_digest_render`
- `provider_request_id`: response ID when present
- `workdir`: repo or job root so project inference stays stable

## Preferred helper

Use `openrouter_post_json(...)` from `/opt/data/scripts/openrouter_spend.py` so the HTTP call and spend recording happen in the same shared code path.

That helper should be the default for new Hermes-owned scripts that call OpenRouter directly.

## Report shape

When reporting spend to DJ, prefer this order:

1. project total: tokens + dollars
2. model total: tokens + dollars
3. workflow/stage total if available
4. recent calls for context only

Avoid reporting only a provider aggregate unless the user explicitly asks for it.

## Verification

After patching a workflow:

- run the script once
- confirm the event appears under the intended project/model in spend summaries
- confirm the workflow/stage metadata is visible for filtering or debugging
- confirm the ledger still writes best-effort and does not block the underlying task
