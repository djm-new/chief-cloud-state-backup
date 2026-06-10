# Briefing staleness guards

Session lesson: a briefing can look plausible while still being wrong if it reuses archived prose instead of current evidence.

## What went wrong
- The executive summary said a group DM ran until `1 AM ET`.
- The latest verifiable Slack message in context was `9:14 ET`.
- The error came from recycling stale archive text into the next briefing, not from the live Slack crawl.

## Guardrails
- Treat archived briefs as history, not source-of-truth evidence.
- Never copy exact timestamps, durations, or "active until" claims from archive text unless the current evidence supports them.
- Prefer rolling state that stores only unresolved topics, decisions pending, and concise summaries.
- If continuity is needed, ingest only the rolling tail of prior briefs, not the full prior executive-summary prose.
- When a time claim matters, cite the current Slack message time or say the latest visible message time and stop there.

## Verification
- Search current briefing inputs for the disputed time claim.
- Confirm the latest verified Slack timestamp before making any duration claim.
- If the evidence is ambiguous, use neutral wording like "active on June 9" or "latest visible message at 9:14 ET."