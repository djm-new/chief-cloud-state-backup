# Auxiliary model spend capture

Hermes has a second, easy-to-miss spend stream outside the main chat turn loop: *auxiliary* model calls.

## What counts as auxiliary spend

Common auxiliary tasks include:
- context compression
- title generation
- session search / retrieval helpers
- vision / web extraction helpers
- other side-channel providers used by `agent.auxiliary_client`

These calls may use different models than the visible chat session. In particular, Anthropic Sonnet/Haiku may appear in logs even when the visible session is on another provider.

## Durable capture rule

Do not assume `state.db` session rows capture all model usage.

For Hermes spend reconciliation:
1. inspect `config.yaml` under `auxiliary:` to see the actual side-task models
2. inspect `agent.log` / gateway logs for auxiliary call sites
3. record auxiliary responses into the spend ledger (`spend.db`) as event-level rows
4. keep accounting best-effort so a ledger failure never breaks chat execution

## Common pattern observed in Hermes

- `auxiliary.compression`, `auxiliary.title_generation`, and `auxiliary.session_search` are the most common hidden spend sources
- these calls may run on a different provider/model than the visible chat session
- if the user asks for Anthropic to be fallback-only, move the *primary* auxiliary slots off Anthropic and leave Sonnet/Haiku only in fallback chains
- these are legitimate Hermes calls and should be attributed separately from the main session model

## Routing hygiene for spend audits

When auxiliary spend looks wrong, inspect `config.yaml` first:
1. `auxiliary.compression`
2. `auxiliary.session_search`
3. `auxiliary.title_generation`
4. any vision/web/browser helper slots
5. `fallback_providers`

A lot of “mystery Anthropic spend” is just hidden side work, not the visible chat provider.

## Implementation note

The shared spend helper should write directly to `llm_usage_events` in `spend.db` and accept raw usage + normalized token/cost fields. Auxiliary adapters should call that helper after a successful response.
