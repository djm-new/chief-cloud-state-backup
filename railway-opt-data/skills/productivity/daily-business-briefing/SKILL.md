---
name: daily-business-briefing
description: "DJ's single ToM-aware Slack/email executive briefing workflow."
version: 1.0.0
author: Hermes Agent
license: private
metadata:
  hermes:
    tags: [briefing, slack, gmail, daily-tom, chief-of-staff]
---

# Daily Business Briefing

Use when configuring, debugging, or running DJ's single integrated smart business briefing.

## Core principle

There is **one** business briefing, not separate Slack/email/ToM reports. The briefing reads DJ's Daily ToM first and uses it as the priority lens for Slack + email review.

Delivery: smart business briefings belong in the Telegram **Briefings** topic (`telegram:-1003956828149:3`), not the alerts topic. Alerts topic 5 is for operational alerts/health checks.

## Safety rules

1. Never send, reply, forward, invite, share, comment, or notify anyone.
2. Never write Slack/email-derived items into the Daily ToM doc without DJ's explicit approval.
3. Suggested ToM additions are approval-required suggestions only.
4. Do not persist raw Slack/email contents to Hermes memory.
5. Keep durable facts/preferences in Hermes memory; keep operational rolling state in files.

## Approved Action list → Daily ToM updates

When DJ explicitly approves adding briefing action-list items to the ToM document, act immediately — this is a permitted Google Docs edit under DJ's policy. Do not ask for another confirmation. Place items where they belong in the current Daily ToM section:

- Flow/company/capital/HR/product items → `Professional`
- MENA/SICO/Olaya/Riyadh/UAE/Saudization items → `Professional - MENA`
- Other workstreams that do not fit the main company list → `Professional - Others`
- Personal items → `Personal`

Operational rules:
1. First inspect the live current ToM via `/opt/data/scripts/daily-tom-context.py` so you can avoid duplicates and understand current sections.
2. Preserve DJ's ToM conventions: `[n:<id>]` IDs, `*` / `**` / `***` priority suffixes, and current section names exactly.
3. Insert newly approved items near the top of their section so they are visible, but keep existing high-priority items intact.
4. Verify with `/opt/data/scripts/daily-tom-context.py` after writing and report only the added items grouped by section.
5. If the direct Google scripts fail because Google API packages are unavailable in system Python, run the one-off Docs API script through `uv run --with google-api-python-client --with google-auth-oauthlib --with google-auth-httplib2 python ...` rather than installing system packages.

## Current files

- Daily ToM sync: `/opt/data/scripts/daily-tom-sync.py`
- Daily ToM context extractor: `/opt/data/scripts/daily-tom-context.py`
- Email context extractor: `/opt/data/scripts/email-tom-context.py`
- Slack collector: `/opt/data/scripts/slack_business_brief_collect.py`
- Slack deterministic pre-filter: `/opt/data/scripts/slack_business_brief_filter.py`
- Briefing context builder: `/opt/data/scripts/slack_business_brief_context.py`
- Rolling state: `/opt/data/slack_brief_archive/open_topics.md`
- Briefing policy: `/opt/data/slack_brief_archive/BRIEFING_POLICY.md`
- Final brief archive directory: `/opt/data/slack_brief_archive/`
- Google security policy: `/opt/data/google-accounts/SECURITY_POLICY.md`
- Attack-vector checklist: `/opt/data/security/ATTACK_VECTOR_CHECKLIST.md`

## Model-routing posture

- Dumb/API work: script-only, no LLM.
- Slack crawl collection: no-agent Python script.
- ToM sync: no-agent Python script.
- Email/ToM/Slack context extraction: deterministic scripts.
- Final executive synthesis: heavier model (`anthropic/claude-sonnet-4-6`) because it requires judgment.
- Simple health summaries: lightweight model (`anthropic/claude-haiku-4-5`).
- Spend reporting must treat briefing runs as LLM usage even when the spend-event table is sparse; session-level usage in the state DB may be authoritative.

See `references/spend-accounting.md` for the merged-session/spend-ledger detail and the dedupe rule.

## Briefing structure

Six sections, always in this order:

1. **Executive summary** — 3-5 bullets max. Most important first. Decisive, not neutral.
2. **Action list additions** — the single consolidated action section. Include everything that should be added to DJ's ToM/action list: decisions needed, suggested ToM additions, monitor/watchlist items that require active follow-up, and carry-forward actions. Opinionated: tell DJ exactly what to do; ask approval for any ToM writes.
3. **Worth knowing / monitor** — brief context only; no action today. One paragraph or less per item.
4. **Carry-forward context** — optional, compact non-action rolling context only. Do not duplicate items already in Action list additions.
5. **Appendix / links** — optional links or provenance if needed.

Do **not** include a dedicated "Deliberately excluded" section in the final briefing by default. Exclusions already create clutter; if DJ explicitly asks what was filtered out, answer in one sentence inline or in a separate follow-up, not as a standing section.

See `references/slack-filter-calibration.md` for detailed content filtering rules.
See `references/briefing-staleness-guards.md` for the archive-reuse / stale timestamp guard that prevents old executive-summary prose from being recycled into new briefs.

## Calibration rules (v3 — validated 2026-05-27)

### The DJ relevance test
Every item must answer: **"Why does DJ need to know this, and what decision or action follows?"**
If the answer is weak → downgrade to "Worth knowing" or exclude. Do not fill the briefing with items that merely exist.

### Feedback ingestion rule
When DJ returns a reviewed briefing with inline comments, treat each comment as calibration data and update the filter/prompt before generating another version. Convert corrections into explicit rules, not just one-off fixes. Common examples from prior calibration: Slackbot app-install requests are irrelevant; DM snippets require surrounding context; tour feedback/leasing wait-time signals can be useful; low-context engineering chatter should be excluded but notable engineering/product decisions should be included.

Latest calibration: do **not** surface old/stale carry-forward just because it exists. If the board meeting already happened, board-meeting preparation items are stale unless there is a fresh explicit decision/action. Resolved low-priority DMs (e.g. someone says they got help elsewhere and does not need DJ) should be excluded, not reported as "worth knowing." Do not tag people as VIPs; prioritize messages by whether they carry actions or information DJ needs, across both DMs/MPIMs and workspace channels.

### Hard exclusions (never include)
- **Slackbot app install requests** — DJ is a workspace super admin and receives these automatically. They are IT's job. Hard-exclude at filter level, never surface in briefing.
- **Pure bot test results / CI channels** — waves-dev-test-automation, test-android-results, backend-dev-testify-automation, application-status, plattest-012n3.
- **Cleaning/housekeeping ops channels** — below DJ level.
- **Platform degradation bot floods** — repeated bot-only degraded/outage lines with no escalation owner or recovery status.

### Always include
- **DMs and MPIMs** — always surface. But MUST read full context (all thread/prior messages) before interpreting. Never quote one line and guess meaning.
- **Exact Daily ToM entities** — Easton, Wynwood, MENA, SICO, Olaya, Hubspot, F&B, Board deck, etc.
- **Deal/acquisition/project channels** — proj-society-wynwood-acquisition, proj-mena, proj-easton, and similar.
- **Money, legal, approval, deadline, investor, board signals** — wire, drawdown, capital, contract, signature, DD, due diligence, data room.

### Include with judgment
- **Tour/prospect signals in leasing channels** — people waiting for tours, prospect visits, staffing gaps at open houses. These ARE valuable to DJ even though "leasing" is otherwise a weak keyword.
- **Engineering items with a named ToM entity** — product naming decisions (e.g., "Society Wynwood → Flow Wynwood"), blockers, or product decisions linked to active deals.
- **Notable engineering discussions** — include when there is a real decision or entity; exclude low-context chatter (PR merges, minor code comments, identity creation, color fixes).

### DM / group-DM handling
- Always surface DMs/MPIMs.
- Read **all context lines** provided before drawing any conclusion.
- If a message is ambiguous without context (e.g., "let's wind him down the week after next"), report: what you know (participants, instruction given), what you don't know (subject), and provide the link. **Do not guess.**
- If context is insufficient: "Group DM with [names] mentions [instruction] — subject not identifiable from available context. Link: [url]."

### False inference rule
- **Never connect unrelated items** as if they are related.
- Example: A Vercel access approval for a MENA app does NOT mean MENA KPI/Hubspot/revenue diagnostic work is unblocked — they are completely separate. Only state connections that are **explicitly** supported by the source material.

### State assertion rule
- **Never assert resolved/closed/complete** unless the source explicitly says so.
- A resolved Google Slides comment is NOT the same as the underlying business question being answered.
- When uncertain: use "unclear," "no explicit confirmation found," or "open question."

### Be opinionated
The briefing should have a confident voice:
- "Read this."
- "This needs a decision."
- "Confirm Tom/Colin are owning the response."
- "Recommend ignoring."
- "Flag to [name]."
- "Quick yes/no from DJ would unblock this."

Do not present items neutrally as "this exists." Tell DJ what to do about it.

### Briefing output structure (enforced)
```
## Executive summary          ← 3-5 bullets max, most important first, decisive
## Action list additions      ← ONE consolidated action section: decisions needed, ToM additions, active follow-ups, watchlist/carry-forward actions; ask approval before writing ToM
## Worth knowing / monitor    ← context only; no action today; do not duplicate action items
## Carry-forward context      ← optional non-action rolling context only; no duplicate action list items
## Appendix / links           ← optional links or provenance if needed
```

Do **not** split action-like items across “Suggested top of mind,” “watchlist,” “carry forward,” “action/decision needed,” and “monitor.” Those collapse into **Action list additions** when they imply DJ should add, decide, follow up, or track something actively.

## Slack filter reference

Detailed channel-by-channel classification decisions, scoring thresholds, anti-patterns, and hard-exclusion rules are documented in:

`references/slack-filter-calibration.md`

Load this when debugging the filter, tuning thresholds, or adding new channels.

## Rolling state discipline

Parking lot state is live ToM state, not legacy Notion state. If you need to debug it, inspect `/opt/data/scripts/daily-tom-sync.py` and the current context output before assuming the feature is gone.

`open_topics.md` should stay compact and operational:

- carry-forward topics
- pending DJ decisions
- suggested ToM additions awaiting approval
- resolved/recently closed items

Do not include raw Slack/email dumps. Keep under 12 KB preferred.

## Archive discipline

Each final briefing should be saved to:

`/opt/data/slack_brief_archive/YYYY-MM-DD-HHMM.md`

Archives are for recall/history. They are not loaded into Hermes memory.

## Health checks

Operational health is checked by:

`/opt/data/scripts/chief_operational_health.py`

It verifies ToM state, Slack latest crawl, email context, filtered Slack context, full context generation, key file sizes, and archive/open-topic presence.

Smart briefing freshness checks must account for lifecycle state:
- if smart briefing jobs are paused, stale briefing artifacts are expected and should not alert;
- if a previously paused briefing has just been enabled and its first scheduled briefing run is still pending, stale prior artifacts are also expected and should not alert;
- only treat stale latest/archive files as issues after an enabled briefing has had a real chance to run.

Daily ToM run/debug details, including the expected context marker, manual run command, manual task additions, Google Docs style preservation, Google runtime venv, marker normalization (✅ for completed, stripped rollover for ↗️), and DST-safe schedule shape, are in `references/daily-tom-troubleshooting.md`.

### Daily ToM context marker troubleshooting

If Chief alerts that Daily ToM context output is missing an expected markdown marker:

1. Reproduce directly: `/opt/data/scripts/chief_operational_health.py`.
2. Run the failing extractor directly: `/opt/data/scripts/daily-tom-context.py`.
3. The Daily ToM extractor must emit the exact marker `## Daily Top of Mind Context` on both success and fallback/error paths; do not let fallback text drift to `## Daily ToM Context` or similar.
4. If Google fetch fails because the runtime Python lacks Google client packages, repair the `/opt/data` Google runtime instead of editing Hermes code:
   ```bash
   uv venv /opt/data/google-accounts/.venv
   uv pip install --python /opt/data/google-accounts/.venv/bin/python \
     google-api-python-client google-auth-oauthlib google-auth-httplib2
   ```
   Then ensure `/opt/data/scripts/google-account` invokes `/opt/data/google-accounts/.venv/bin/python` when present, falling back to `python3` only if the venv is absent.
5. Verify with `/opt/data/scripts/chief_operational_health.py`; expected final line is `Status: OK`.
6. If recent `>` items are missing `↗️`, normalize the live source day with exact Docs API `replaceAllText` requests for the raw lines, then re-run `/opt/data/scripts/daily-tom-context.py` to confirm the marker appears in context.

## Attack-vector review

Before installing/running new external skills, scripts, or dependencies, read:

`/opt/data/security/ATTACK_VECTOR_CHECKLIST.md`

Default posture: if unclear, stop and ask DJ before running.
