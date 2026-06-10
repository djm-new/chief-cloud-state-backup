# Spend reporting dimensions

Use this when rendering Hermes spend summaries so the report is hard to misread.

## Required per-model fields
- raw estimated cost
- reported/calibrated cost
- calibration factor (or `none`)
- pricing source
- pricing version
- status flags (`estimated`, `included`, `unknown`)
- provider / model label

## Rules
- Do not show a single cost number without indicating whether it is raw or calibrated.
- Do not collapse `estimated` and `included` into a single label.
- Do not apply calibration globally unless the provider has a real external anchor.
- Keep the raw ledger intact; calibration is a report-layer view only.
- For mixed sessions, prefer per-call aggregation over final session provider attribution.
- If `actual billed spend` has no real feed, print `unavailable` instead of `0`.

## Current Hermes convention
- Anthropic may be calibrated in reporting when an external console total is available.
- OpenAI Codex and OpenRouter/Qwen/DeepSeek remain raw token-based estimates unless separately anchored.
- Subscription-included routes still get token-based estimated API-equivalent cost for visibility.
