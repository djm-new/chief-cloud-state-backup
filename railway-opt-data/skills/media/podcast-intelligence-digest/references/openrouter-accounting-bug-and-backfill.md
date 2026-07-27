# OpenRouter accounting bug and backfill

## Symptom

Podcast rows in the Hermes spend ledger appeared with `0` tokens and `$0.00` even though the raw OpenRouter response showed real `prompt_tokens`, `completion_tokens`, and `cost`.

## Root cause

`/opt/data/scripts/openrouter_spend.py` passed a raw `dict` into `agent.usage_pricing.normalize_usage(...)`.

That helper expects attribute-style access for response usage fields, so the dict payload was not normalized correctly.

## Fix

- Convert raw usage dicts into an attribute-access object before calling `normalize_usage(...)`.
- Keep using the shared `openrouter_post_json(...)` helper so future scripts record usage automatically.

## Backfill rule

When this bug is found in historical artifacts:

- read `raw_usage_json`
- recompute canonical token buckets
- update `input_tokens`, `output_tokens`, `prompt_tokens`, `total_tokens`, `reasoning_tokens`, and `estimated_cost_usd`
- verify the corrected totals at the project/workstream level

## Verification

After the fix, the podcast digest ledger should show nonzero values for the podcast project in both:

- `sum(total_tokens)`
- `sum(estimated_cost_usd)`

for recent runs that actually invoked OpenRouter.