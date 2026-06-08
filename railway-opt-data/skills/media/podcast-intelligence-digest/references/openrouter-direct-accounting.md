# Direct OpenRouter Accounting for Podcast Scripts

Use when the podcast pipeline uses OpenRouter from standalone scripts rather than only through Hermes agent sessions.

## What changed in this workflow

- Legacy/raw `requests.post(...)` calls to OpenRouter are easy to miss in Hermes spend reporting.
- The preferred implementation is the shared helper in `/opt/data/scripts/openrouter_spend.py`:
  - `openrouter_post_json(...)` for request + accounting in one path
  - `record_openrouter_usage(...)` when the response was fetched elsewhere
- For spend reporting, use the OpenRouter `usage` object returned by the API response, especially `usage.cost`, `prompt_tokens`, `completion_tokens`, and `total_tokens`.

## Practical implication

If a Hermes spend briefing only sees `openai-codex` but the podcast project is actively using Qwen/OpenRouter, the briefing is incomplete rather than the podcast job being idle.

## Verified example shape

- Episode scoring pass prints per-batch usage lines.
- Daily digest render writes a markdown artifact with a hidden HTML header containing model and usage metadata.
- The wrapper script extracts the final digest artifact and delivers only the cleaned text.

## Recommended reporting rule

For podcast work, report both:

- **Hermes-session spend** for agent-run tasks
- **Direct OpenRouter spend** for standalone scripts

Do not merge them silently; label them separately so the user can see what is and is not being counted.

## Preferred implementation rule

New code should use the shared helper so the spend ledger is updated automatically. Treat raw HTTP calls as legacy-only unless you have a very specific reason to bypass the helper.