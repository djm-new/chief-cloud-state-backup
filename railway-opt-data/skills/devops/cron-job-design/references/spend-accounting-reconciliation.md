# Spend Accounting Reconciliation for Cron-Delivered Briefings

## When to use
Use this when a cron-delivered briefing or alert is visibly generated, but the spend ledger shows zero or missing token usage for the same window.

## Reconciliation steps
1. **Identify the exact cron job and run time** from `/opt/data/cron/output/<job_id>/...md`.
2. **Confirm whether the job is script-only** (`no_agent: true`). Script-only jobs can deliver messages with zero LLM spend.
3. **If the job is LLM-backed, inspect the spend DB window around the run time**:
   - query `llm_usage_events`
   - check `provider`, `model`, `source`, `platform`, `project_slug`, and `estimated_cost_usd`
4. **Compare the archive artifact to the spend ledger**:
   - archive exists and contains synthesized content
   - spend rows exist near the run time
   - if archive exists but no spend rows do, the accounting hook is missing or the run happened through an uninstrumented path
5. **Check for project attribution gaps**:
   - empty `project_slug`
   - missing `channel_label`
   - generic `source=cron` / `platform=cron` rows that belong to another project
6. **Differentiate between message delivery and token spend**:
   - Telegram delivery itself costs no tokens
   - only actual model calls should create spend rows

## Useful probes
- `search_files` / `read_file` on `/opt/data/cron/output/<job_id>/`
- SQL against `/opt/data/spend.db`
- archive lookup in `/opt/data/slack_brief_archive/`

## Common failure modes
- A briefing is clearly model-generated, but the cron wrapper never calls `record_spend_event()` on the final response path.
- The model ran, but the usage record landed in the wrong `project_slug` or with empty attribution.
- The job was a script wrapper that emitted the user-facing text but delegated the actual LLM work elsewhere.

## Outcome label
If the content was produced by an LLM but there is no corresponding spend row, label the issue as **accounting gap**, not **zero spend**.
