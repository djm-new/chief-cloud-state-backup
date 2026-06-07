# Hermes Spend Monitor / Native Cost Ledger

Use this when the user asks to track Hermes model spend, token consumption, or cost by provider/model/project/channel.

## Design lesson

Provider dashboards are insufficient for Hermes because they usually answer “what did this API key spend?” but not “which Hermes project, platform channel, cron job, or session spent it?” Attribution must happen at the Hermes model-call boundary.

Preferred architecture:
1. **Local event ledger**: record one SQLite row per successful model response.
2. **Use existing token/cost normalization**: Hermes already normalizes provider usage and estimates costs in `agent.usage_pricing`.
3. **Provider reconciliation later**: OpenRouter/Anthropic/OpenAI reported totals can be pulled periodically, but local events remain the source of attribution.

## Implementation pattern

- Store the event ledger separately from session state, e.g. `$HERMES_HOME/spend.db`, to keep per-call accounting low-risk and independent from session schema migrations.
- Add a module like `agent/spend_ledger.py` with:
  - `SpendEvent` dataclass
  - `record_spend_event(...)`
  - `summarize_spend(days, group_by, limit)`
  - `recent_events(limit)`
  - helpers to infer `project_slug` from git root / workdir and build human channel labels.
- Instrument the existing model response usage block in `run_agent.py` after `normalize_usage(...)` and `estimate_usage_cost(...)`, near where session token counters are incremented.
- Make ledger writes best-effort: catch/log errors and never break chat or tool execution.

Useful fields per row:
- timestamp, provider, model, api_mode, base_url
- session_id, parent_session_id, source/platform
- chat_id, chat_name, chat_type, thread_id, gateway_session_key
- channel_label, workdir, project_slug
- input/output/cache/reasoning/prompt/total tokens
- estimated_cost_usd, cost_status, cost_source, pricing_version
- latency_ms, provider_request_id, raw_usage_json, metadata_json

## CLI shape

Add a lightweight `hermes spend` CLI with group-by views:

```bash
hermes spend                    # default summary by provider
hermes spend provider --days 7
hermes spend model --days 7
hermes spend project --days 7
hermes spend channel --days 7
hermes spend source --days 7
hermes spend session --days 7
hermes spend recent --limit 20
```

Keep output text-first and scan-friendly:

```text
Hermes Spend — last 7 days

Total estimated: $18.42
Model calls:     128
Tokens:          1,234,567 total · 900,000 in · 334,567 out

By project:
- healthos: $8.75 · 41 calls · 420,000 tokens
- daily-briefing: $4.10 · 12 calls · 190,000 tokens
```

## Telegram/channel naming preference

For DJ, never present Telegram topics as numeric labels like “topic 5” in user-facing spend reports or explanations. Use human-readable names when available. If Hermes only has numeric IDs, prefer the human group/chat label and say the exact topic name is unresolved; ask for/derive a mapping rather than exposing “topic N” as the label.

## Tests and verification

Targeted tests should cover:
- recording two provider events and summarizing by provider/project/channel
- recent event ordering
- project slug inference from nested git-root workdirs
- CLI rendering empty state and grouped totals

If `pytest` is not installed in the checkout, use repo tooling such as:

```bash
uv run --with pytest --with pytest-xdist pytest tests/agent/test_spend_ledger.py tests/hermes_cli/test_spend.py -q
```

Also run syntax checks on touched modules:

```bash
python3 -m py_compile agent/spend_ledger.py hermes_cli/spend.py run_agent.py hermes_cli/main.py
```

## Pitfalls

- Do not infer spend after the fact from transcripts if you can instrument the model-call boundary.
- Do not rely on provider dashboards for channel/project attribution.
- Do not append numeric Telegram thread/topic IDs to user-facing channel labels for DJ.
- Do not let accounting writes affect model calls; ledger persistence must be best-effort.
- `argparse` parent/default values can leak into subcommands. For `hermes spend project`, prefer the subcommand name over a hidden parent `--by` default when deciding group-by dimension.
