# Codex OAuth auxiliary fallback

Session pattern:
- Main Hermes chat can stay on `openai-codex` via OAuth.
- Hidden helper paths (`auxiliary.compression`, `auxiliary.title_generation`, `auxiliary.session_search`) may fail with `401 token_expired` even when `hermes auth status openai-codex` says logged in.

Recommended recovery:
1. keep the main Codex OAuth credential in place
2. move hidden helpers off Codex if they are the failure source
3. prefer `openrouter` + `deepseek/deepseek-v4-pro` when the user wants to avoid Anthropic for these helpers
4. verify by checking `config.yaml` and restarting/reloading the gateway so the new auxiliary routing is active

Why this matters:
- The visible chat loop can be healthy while only the helper path is stale.
- “Token expired” on helpers is often a routing problem, not a global auth outage.
- If the user explicitly wants no Anthropic, OpenRouter/DeepSeek is a good low-friction fallback for these auxiliary slots.
