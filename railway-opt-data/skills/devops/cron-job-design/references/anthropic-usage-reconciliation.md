# Anthropic usage reconciliation notes

Session finding:
- The Anthropic Usage dashboard for API key `chief-hermes` showed substantial token usage for today, grouped by model (`claude-sonnet-4-6`, `claude-haiku-4-5-20251001`).
- The dashboard explicitly says the token usage chart includes usage from both **API and Console**.

Implication for Hermes spend reporting:
- A Hermes local session ledger can undercount Anthropic activity if some usage is coming from Console-side activity or from sessions that are not correctly attributed locally.
- When a local estimate disagrees with Anthropic’s dashboard, reconcile against the Anthropic Usage/Cost Admin API or dashboard export, not the local session DB alone.

Attribution checklist:
1. Compare Anthropic dashboard totals for the API key and day.
2. Compare Hermes session DB rows for the same day.
3. Check gateway logs for long Sonnet/Haiku sessions and cron runs.
4. Treat unlabeled or missing-provider sessions as attribution gaps, not zero spend.
