# Telegram topic model routing notes

Use when DJ wants different Hermes models by Telegram topic in the Chief Group.

## Current Chief Group map

Chat: `-1003956828149`

- topic `1` = General/home
- topic `3` = Archive/Old Chief
- topic `4` = Briefings
- topic `5` = Alerts
- topic `6` = Daily Brain Dump
- topic `7` = Coding
- topic `8` = General (DJ's ad-hoc/conversational topic)

## Default routing

- Default (all topics unless overridden): `openai-codex` / `gpt-5.4-mini`
- Coding topic 7: `openai-codex` / `gpt-5.5`
- Fallback chain: `openrouter` / `deepseek/deepseek-v4-pro` → `anthropic` / `claude-opus-4-6`

## Per-topic model overrides (config.yaml)

```yaml
telegram_topic_model_overrides:
  "-1003956828149":
    "7":
      provider: openai-codex
      model: gpt-5.5
    "8":
      provider: anthropic
      model: claude-opus-4-6   # example: DJ requested for a session
```

Overrides live in `/opt/data/config.yaml` under `telegram_topic_model_overrides`.

**IMPORTANT: Overrides do NOT auto-revert on `/new` or session reset.** They are config-level
and persist until manually removed. When DJ says "for this session only", warn them and offer
to revert at the end of the session (or immediately when they say "switch back to default").

To revert topic 8 to default gpt-5.4-mini:
```yaml
    "8":
      provider: openai-codex
      model: gpt-5.4-mini
```
Or remove the `"8"` block entirely.

Also revert the **global default** if it was changed during the session:
```bash
/opt/hermes/.venv/bin/hermes config set model.provider openai-codex
/opt/hermes/.venv/bin/hermes config set model.default gpt-5.4-mini
```

## Session-scoped vs config-level overrides

- **Session-scoped** (via `/model` slash command in-session): stored in `_session_model_overrides`
  dict in gateway memory, cleared on `/new` or gateway restart.
- **Config-level** (editing `config.yaml`): survives restarts and new sessions.

DJ's "for this session only" requests map to config-level changes (we don't have a better
mechanism). Always clean up at the end or when DJ says "switch back to default".

## How to apply a topic override (preferred method)

`hermes config set` is unreliable for deeply nested YAML keys. Patch config.yaml directly:

```python
# Read the section and patch:
from pathlib import Path
import re
p = Path('/opt/data/config.yaml')
# ... use patch() tool or manual YAML edit
```

Or use the `patch` file tool to do a targeted text replacement on the relevant block.
Verify after with `tail -10 /opt/data/config.yaml`.

## Anthropic Opus 4.6 fast mode

- Fast mode (`speed: fast`) is supported **only on `claude-opus-4-6`**.
- Opus 4.7+ explicitly rejects the `speed` param with HTTP 400.
- Hermes auto-injects `speed: fast` when it detects `opus-4-6` via `_supports_fast_mode()`.
- Effect: ~2.5x faster output throughput at the same price ($5/$25 per M input/output tokens).
- Opus 4.6 and 4.7 are **identical price** — fast mode is the key differentiator for conversational use.

## Model selection guide for DJ

| Use case | Provider | Model |
|---|---|---|
| Default conversation | openai-codex | gpt-5.4-mini |
| Coding | openai-codex | gpt-5.5 |
| Fast conversational Anthropic | anthropic | claude-opus-4-6 (fast mode auto) |
| Latest Anthropic | anthropic | claude-opus-4-7 (no fast mode, same price) |
| Compression / auxiliary | anthropic | claude-sonnet-4-6 |

Note: "Claude Opus 4.8" does not exist in Hermes or Anthropic's lineup as of this session.
Current Hermes build knows: `claude-opus-4-5`, `claude-opus-4-6`, `claude-opus-4-7`.
"Sonnet 4.8" also does not exist — confirm model names against `usage_pricing.py` if unsure.

## Verification after a change

```bash
tail -5 /opt/data/config.yaml
/opt/hermes/.venv/bin/hermes config | grep -A4 "Model:"
```

Note: the running gateway picks up config.yaml changes on the next inbound message — no
restart needed for topic overrides. The current in-flight session still uses the old model
until the next turn.

## Communication pitfall

DJ uses "API" to mean paid OpenAI API-key billing. Hermes logs say `API call` for any model
request, including OAuth Codex. When explaining, say: "Hermes logged a model request, but it
is routed through `openai-codex` OAuth at `chatgpt.com/backend-api/codex`, not the paid
`api.openai.com/v1` provider." Keep this concise.
