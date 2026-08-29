# Production product eval after deploy

Use when deploying an app where DJ cares about end-user behavior, not just process health.

## Pattern

1. Push and wait for the deploy mechanism to complete for the exact commit SHA.
2. Verify health/readiness, but treat it as a prerequisite only.
3. Run the app's own product/user-flow eval against the production URL.
4. If production eval fails, fix the product behavior, re-run local tests, commit, push, wait for deploy, and rerun the production eval.
5. Only call the deploy complete after the product eval passes.

## Example: Ben Bot

Ben Bot's product eval script expects the chat endpoint as its first positional argument, not a `--base-url` flag:

```bash
/opt/hermes/.venv/bin/python scripts/run_product_interaction_eval.py \
  https://ben-bot-production.up.railway.app/chat
```

A passing deployment should verify all of:

```bash
curl -fsS https://ben-bot-production.up.railway.app/health
/opt/hermes/.venv/bin/python scripts/run_product_interaction_eval.py \
  https://ben-bot-production.up.railway.app/chat
```

## Pitfalls

- A green GitHub Actions deploy and a 200 `/health` can still leave user-facing behavior broken.
- Do not retry the exact same failed product eval without changing the code or diagnosis.
- Generated artifacts that are locally modified but not part of the deploy should be left unstaged unless they are intentionally updated outputs.
