# OpenRouter model aliases and setup notes

## Kimi K3 / Kimi 3
- OpenRouter model ID: `moonshotai/kimi-k3`
- Enabling it in Hermes does **not** require a separate per-model API key.
- Use your existing `OPENROUTER_API_KEY` and switch Hermes to the model ID above.
- Model/provider changes apply to new sessions or the next gateway model load.

## Practical reminder
When a user asks to "enable" an OpenRouter model, the key task is usually to set the exact model string, not to add a new credential.
