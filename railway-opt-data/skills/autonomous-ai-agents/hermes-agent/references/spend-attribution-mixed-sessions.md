# Mixed-Session Spend Attribution

Use this when Hermes sessions can switch providers mid-conversation.

## Why this matters

A single Telegram or CLI session may include:
- OpenAI Codex for the main turn loop
- Anthropic for fallback or auxiliary work
- OpenRouter Qwen / DeepSeek for heavy podcast or reasoning workloads
- model switches mid-session when a fallback or helper path takes over

If reporting reads only the *final* session row, it can hide earlier spend under the wrong provider. The correct unit is the **per-call spend event**, not the session summary row.

## Reliable attribution rule

Prefer `llm_usage_events` rows keyed by:
- `created_at`
- `provider`
- `model`
- `session_id` / `parent_session_id`
- `source` / `platform`
- token counts + estimated USD

Then roll up by:
- provider
- model
- project/workdir
- channel/platform
- session_id only when the user explicitly wants session-level totals

## Mixed-session symptoms

If the ledger seems wrong, check for:
- a session whose last row is `openai-codex` but earlier assistant/helper calls are Anthropic
- lots of auxiliary calls in `agent.log` / `gateway.log` with a different provider than the final session row
- a report showing `$0` or near-zero for a provider that visibly appears in logs
- OpenRouter-heavy sessions where Qwen/DeepSeek should be counted separately from Hermes chat turns

## Reconciliation workflow

1. Query the spend ledger for the last 7 days by provider and model.
2. Compare that against `state.db` session aggregates.
3. If the totals disagree, trust the event ledger first.
4. Backfill missing events from rotated logs when the ledger was empty or partially wired.
5. Use provider dashboards only as a coarse cross-check when the API gives no direct per-call billing feed.

## Verification snippets

```bash
# Ledger rollup
sqlite3 /opt/data/spend.db "SELECT provider, model, COUNT(*), ROUND(SUM(COALESCE(estimated_cost_usd,0)), 2) FROM llm_usage_events WHERE created_at >= strftime('%s','now','-7 day') GROUP BY provider, model ORDER BY 4 DESC;"

# Session-state cross-check
sqlite3 /opt/data/state.db "SELECT billing_provider, model, COUNT(*) FROM sessions WHERE started_at >= strftime('%s','now','-7 day') GROUP BY billing_provider, model ORDER BY 3 DESC;"
```

If the session-state rollup is lower or shows a different provider mix, that usually means the session changed providers mid-stream and only the event ledger is telling the truth.