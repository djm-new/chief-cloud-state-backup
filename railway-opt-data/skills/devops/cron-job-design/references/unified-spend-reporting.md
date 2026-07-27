# Unified Hermes spend reporting architecture

Rebuilt 2026-07-17 after DJ rejected briefings that showed `$0.0000` next to
millions of tokens and "No workstreams found." This is the reference for how
`/opt/data/scripts/spend_report_helper.py` builds the daily/weekly briefings.

## Data sources (merge, in this priority)

1. **`/opt/data/state.db` `sessions` table** — the complete usage record for
   every agent session (telegram/cron/cli/api): token buckets
   (input/output/cache_read/cache_write), model, `billing_provider`,
   `billing_mode`, `estimated_cost_usd`, `title`, `source`.
2. **`/opt/data/spend.db` `llm_usage_events`** — script-level LLM calls that
   are NOT agent sessions (podcast digest OpenRouter calls with
   `metadata_json.workflow`/`stage`). **Dedupe rule:** exclude any row whose
   `session_id` exists in the sessions table, or usage double-counts.
3. **`/opt/data/cron/jobs.json`** — cron session ids look like
   `cron_<job_id>_YYYYMMDD_...`; map to job names. Field is `id`, **not**
   `job_id`.
4. **`/opt/data/sessions/sessions.json`** — gateway session-key → session_id
   index; keys look like `agent:main:telegram:group:<chat_id>:<topic_id>`.

## Cost model: report API-rate value, not just billed cost

- Codex (`openai-codex` provider, `billing_mode=subscription_included`)
  records `estimated_cost_usd = 0.0`. That is *billed* truth but useless as a
  report — DJ wants the estimated dollar value of the usage.
- Compute `est_cost` per session/event from token buckets × OpenRouter
  reference rates; label it "Estimated spend (API-rate value)" and show
  billed status separately ("unavailable (Codex usage is
  subscription-included)").
- Pricing lookup order: `agent.usage_pricing.get_pricing_entry(model,
  provider='openrouter')` when Hermes is importable, else direct
  `https://openrouter.ai/api/v1/models` fetch with key from env or
  `/proc/1/environ`. Cache to `pricing_cache.json` with 7-day TTL so the
  5AM cron works offline.
- **OpenRouter id aliasing:** Anthropic models use dotted versions —
  `claude-sonnet-4-6` resolves as `anthropic/claude-sonnet-4.6`. Generate
  candidates: raw name, vendor-prefixed (`claude*`→anthropic, `gpt*`→openai,
  `kimi*`→moonshotai, `qwen*`→qwen), and dotted variant
  (`re.sub(r"(\d+)-(\d+)$", r"\1.\2", base)` — note the group must NOT
  consume the preceding dash, or you get `sonnet.4.6`).
- Ledger events with a recorded `estimated_cost_usd > 0` (e.g. podcast
  OpenRouter rows priced `provider_models_api`) keep that number as the est.

## Telegram topic attribution (the hard part)

- The gateway index only stores the *current* session per topic — `/new`
  overwrites it, so historical attribution is lost unless you accumulate.
- Persist a snapshot (`session_topics.json`) on every report run.
- Propagate labels through the session graph in `state.db`:
  - `parent_session_id` links (both directions);
  - **reset pairs**: a session with `end_reason='session_reset'` whose
    `ended_at` is within ~5s of another telegram session's `started_at` is
    the same topic continuing under a new id. This is how resets without
    parent links still get labeled.
- BFS from all labeled nodes. Verified: this correctly attributed a 1.4M-token
  session that naive mapping left as "unmapped".
- Topic id map for the Chief group (best-effort): 1=General/home,
  3=Archive, 4=Briefings, 5=Alerts, 6=Daily Brain Dump, 7=Coding,
  8=General (ad-hoc). 4/5/6 confirmed via cron delivery targets; 7 via the
  `telegram_topic_model_overrides` config + observed usage.

## Report shape that landed well

Per window (24h + 7d): tokens with in/out/cache split, estimated spend
(API-rate value), billed status, activity counts. Then: **By project**
(Cron: <job name>, Telegram: <topic>, CLI, Script: <workflow>), **By
Telegram topic**, **By model** (with subscription-included tag), **Script
stages** (workflow — stage), **Top sessions** (title, model, ~est).

## Verification

- `HERMES_SPEND_REPORT_FORCE=1` for both scripts, under BOTH interpreters
  (`/opt/hermes/.venv/bin/python` and system `python3`) — the daily wrapper
  uses the venv python, the weekly cron uses system python.
- Check `unpriced_tokens` is 0 in the JSON dump
  (`python3 spend_report_helper.py 30`).
- Mirror every change to
  `/opt/data/github/chief-cloud-state-backup/railway-opt-data/scripts/` and
  `py_compile` both trees.
- When verifying output, redirect to a file — piping to `head` raises
  BrokenPipeError and looks like a crash.
