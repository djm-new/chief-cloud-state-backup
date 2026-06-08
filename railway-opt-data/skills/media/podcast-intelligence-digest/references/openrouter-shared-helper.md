# Shared OpenRouter helper for podcast scripts

Use the shared helper in `/opt/data/scripts/openrouter_spend.py` for any Hermes-owned script that calls OpenRouter directly.

## Preferred API

- `gateway_env_key()` — resolves `OPENROUTER_API_KEY`, falling back to `/proc/1/environ` for gateway env visibility.
- `build_openrouter_headers(...)` — standardizes `Authorization`, `Content-Type`, `HTTP-Referer`, and `X-Title`.
- `openrouter_post_json(...)` — posts to OpenRouter and automatically records spend from the response `usage` block.
- `record_openrouter_usage(...)` — normalize usage and persist a spend event when the response has already been fetched elsewhere.

## Why this matters

- New podcast scripts should not hand-roll `requests.post(...)` + ad hoc accounting.
- The helper keeps token tracking, cost estimation, and ledger writes aligned for every new project that follows the pattern.
- Use a stable `project_slug`, `source='cron'`, `platform='cron'`, and a stage name in metadata so reports can separate discovery, scoring, and render passes.

## Rollout pattern

1. Put the helper in the shared scripts module, not inside the individual podcast script.
2. Switch live scripts to `openrouter_post_json(...)`.
3. Update reusable skill templates so future projects inherit the helper path.
4. Verify with `python3 -m py_compile ...` and a search for direct `openrouter.ai/api/v1/chat/completions` URLs under the active script tree.

## Practical note

If a script still needs custom response handling, call `openrouter_post_json(...)`, then read `data['choices'][0]['message']['content']` and `data.get('usage', {})` from the returned payload.
