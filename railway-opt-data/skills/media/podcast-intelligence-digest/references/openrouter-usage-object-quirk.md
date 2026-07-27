# OpenRouter usage-object quirk

During a spend review, the podcast pipeline was found to be passing `data.get('usage', {})` directly into `agent.usage_pricing.normalize_usage(...)`.

Why this matters:
- `normalize_usage()` expects attribute access (`usage.prompt_tokens`, `usage.completion_tokens`, etc.).
- A raw dict can therefore normalize to zero tokens/cost, even when the OpenRouter response contains real usage.

Fix pattern:
- Convert dict payloads to an attribute-style object before normalization, or update the helper to do so internally.
- Backfill `llm_usage_events` from `raw_usage_json` for any historical rows written while the bug existed.

Verification:
- Add a regression test that loads the helper, passes a dict usage payload, and asserts the canonical usage and spend event are nonzero.
