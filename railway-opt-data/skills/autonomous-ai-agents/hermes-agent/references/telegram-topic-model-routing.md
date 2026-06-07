# Telegram topic model routing notes

Use when DJ wants different Hermes models by Telegram topic in the Chief Group.

## Current Chief Group map

Chat: `-1003956828149`

- topic `1` = General/home
- topic `3` = Archive/Old Chief
- topic `4` = Briefings
- topic `5` = Alerts
- topic `6` = Daily Brain Dump
- topic `7` = Coding 1
- topic `8` = Coding 2

## Desired routing pattern

- Default/all non-coding topics: `openai-codex` / `gpt-5.2`
- Coding topics 7 and 8: `openai-codex` / `gpt-5.5`
- Fallback: `anthropic` / `claude-opus-4-6`

## Config shape

```yaml
model:
  provider: openai-codex
  default: gpt-5.2

fallback_providers:
- provider: anthropic
  model: claude-opus-4-6
  base_url: ''

telegram_topic_model_overrides:
  "-1003956828149":
    "7":
      provider: openai-codex
      model: gpt-5.5
    "8":
      provider: openai-codex
      model: gpt-5.5
```

## Verification

After restart/redeploy, inspect live logs, not memory:

```bash
head -12 /opt/data/config.yaml
/opt/hermes/.venv/bin/hermes gateway status
tail -80 /opt/data/logs/agent.log | grep -E 'conversation turn:|API call #|provider=openai-codex|provider=anthropic|Telegram topic model override'
```

For a topic-specific check, send a short message in Coding 1/2 and verify logs show:

```text
Telegram topic model override: chat=-1003956828149 thread=7 gpt-5.2 -> gpt-5.5 provider=openai-codex
conversation turn ... model=gpt-5.5 provider=openai-codex
```

General should show `model=gpt-5.2 provider=openai-codex`.

## Communication pitfall

DJ uses “API” to mean paid OpenAI API-key billing. Hermes logs say `API call` for any model request, including OAuth Codex. When explaining, say: “Hermes logged a model request, but it is routed through `openai-codex` OAuth at `chatgpt.com/backend-api/codex`, not the paid `api.openai.com/v1` provider.” Keep this concise.
