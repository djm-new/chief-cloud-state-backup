# Cron self-heal + spend briefing lessons

Session-specific notes from fixing a recurring cron failure and a misleading spend report.

## Self-heal monitor pattern
- Scan `/opt/data/cron/output/*/` for recent Markdown outputs containing stack traces or known failure markers.
- Deduplicate with a state dir, e.g. `seen_failures.json` plus `last_scan_epoch.txt`, so old failures are not reprocessed.
- For exact, deterministic signatures, patch the live script in place and verify immediately with `bash -n`, `python -m py_compile`, or a dry run.
- Only notify when a fix was applied or human input is still needed; stay silent on healthy runs and on repeated already-seen failures.
- If the same script is mirrored in a backup checkout, patch every runtime copy.

## Spend briefing lesson
- If the ledger shows `estimated_cost_usd = 0.0` but all sessions are marked `cost_status='included'` / subscription-included, do not present that as a broken report.
- Render the report as `Estimated spend: $0.0000 (subscription-included)` and add `Billed spend: unavailable`.
- Surface `Included sessions: N` so the zero is explained by billing mode, not by missing usage.
- For stripped cron runtimes, keep spend aggregation behind a helper that can read `/opt/data/spend.db` directly and resolve `HERMES_HOME` from the environment or `~/.hermes`.

## Known repair examples
- Broken import in spend briefing: replace `from agent.spend_ledger import summarize_spend` with the shared local helper import.
- GitHub backup sync auth: patch literal placeholder auth URLs so they interpolate the real token variable at runtime.
