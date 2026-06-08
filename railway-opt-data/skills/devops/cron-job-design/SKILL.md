---
name: cron-job-design
description: "Design, write, and debug Hermes cron jobs: output discipline, alert patterns, script-only vs agent jobs, dedup, and delivery targeting."
version: 1.0.0
author: hermes-agent
platforms: [linux]
metadata:
  hermes:
    tags: [cron, monitoring, alerting, scripting, devops, railway]
    related_skills: [hermes-agent, webhook-subscriptions]
---

# Cron Job Design

Guidance for writing cron scripts and cron job configurations that are genuinely useful — not noisy, not useless — for Hermes gateway deployments (Railway, Docker, local).

---

## Core principle: silent on OK, actionable on alert

**DJ explicitly flagged raw status dumps as "entirely useless."**

A cron job that fires every N minutes and delivers verbose stats even when nothing is wrong is noise. The right model:

- **Silent when OK.** Output nothing. The cron delivery system only sends output to Telegram (or wherever) if the script prints something.
- **Use exactly three states when you do alert:**
  1. **OK** — everything is fine; no DJ action.
  2. **Warning** — something is off but not broken; say what is wrong and what DJ needs to do.
  3. **Broken** — something is broken; say what is broken and what DJ needs to do now.
- **Alert only when something actionable is happening.** The output must answer: *what broke, what context do I need to understand it, and what exact action does DJ need to take?* If the action is for Hermes, say `DJ action: none. Hermes should ...` explicitly.
- **Never send a raw status block** — not memory/disk/process stats, not file ages, not check counts. Those belong in a status file written to disk for later inspection, not pushed to the user proactively.

## Report jobs: daily + weekly, with truthful zeroes

Spend-style report jobs are not health alerts. They should be designed as **explicit daily and weekly summaries** with stable cadence and unambiguous windows.

Rules:
- **Daily and weekly should both exist** when the user asks for both. Do not assume a daily job covers the weekly need.
- **Report the actual ledger result, even if it is zero.** If spend is `0.0000` or the pricing source is `included`, say that plainly instead of implying failure or activity.
- **Do not infer work happened from the existence of a scheduled run.** A successful cron wakeup is not evidence that any spend events occurred.
- **Call out pricing caveats explicitly.** If `estimated_cost_usd` is zero because the provider or pricing path is still unresolved, the report should surface that as a caveat, not hide it.
- **Use the same source of truth for both cadence variants** so the daily and weekly numbers reconcile (same ledger, different window).

For spend reports, the primary question is: *what did the ledger record in the window?* Not: *did the job run?*

---

## Alert output format

When there IS something DJ-actionable, the alert message should be:

```
⚠️ <System> needs DJ attention
Time: <ISO UTC>

What changed:
- <issue 1>
- <issue 2>

Useful context:
- <metric 1>: <value>
- <metric 2>: <value>

[Optional: Recent severe log lines:]
<log tail>

[Optional: Operational issue details:]
- <detail>

DJ action: <specific action required>
```

If the recommended DJ action is `none`, do **not** label it "needs attention." Either stay silent (preferred for recurring monitors) or label it clearly as internal follow-up, e.g. `ℹ️ <System> Hermes follow-up logged` with `DJ action: none.`

Key rules:
- Lead with emoji flag so it's scannable in Telegram.
- "What changed" = the issues list, bullet-formatted.
- "Useful context" = metrics only when the issue could be caused by resource pressure.
- Never combine "needs attention" with "DJ action: none." That is contradictory and DJ explicitly rejected it.

## LLM-backed cron jobs: use the shared accounting helper

When a cron job calls OpenRouter directly from a script, prefer the shared helper pattern used by Hermes-owned scripts instead of hand-rolling `requests.post(...)` plus ad hoc usage logging.

Guideline:
- centralize request + spend recording in a shared helper;
- attach stable metadata like `project_slug`, `source`, `platform`, and a stage name;
- verify the rollout by compiling the changed scripts and searching for lingering direct OpenRouter URL calls in the active script tree.

This keeps token tracking, cost estimation, and ledger attribution aligned across future projects.

## Spend reports: use the session insights path, not the raw ledger

For Hermes daily/weekly spend reporting, the authoritative reporting source is the *session insights* path (`SessionDB` + `InsightsEngine`), not the narrower `agent.spend_ledger` table alone.

Why:
- the raw ledger can show only a partial view of spend attribution;
- `InsightsEngine.generate(days=...)` already exposes `estimated_cost` and `actual_cost` plus session/model/platform breakdowns;
- daily and weekly reports should answer: estimated spend, actual billed spend, sessions, tokens, and the top models/platforms driving cost.

Recommended reporting shape:
- *Daily*: last 24h estimated spend, actual billed spend, sessions, tokens, included sessions, unknown pricing sessions, top models, top platforms.
- *Weekly*: last 7d estimated spend, actual billed spend, sessions, tokens, included sessions, unknown pricing sessions, top models, top platforms.

If a spend report prints `$0.0000`, do not assume the report is healthy. Check whether the data path is using the session insights engine or a ledger that undercounts/omits the relevant fields.

Support files:
- `references/spend-reporting.md`
- `references/chief-alert-triage.md`

Repeated identical alerts are noise. Use a fingerprint+cooldown pattern in bash scripts:

```bash
ALERT_FINGERPRINT_FILE="$STATE_DIR/last_alert_fingerprint.txt"
ALERT_LAST_SENT_FILE="$STATE_DIR/last_alert_sent_at"
ALERT_REPEAT_AFTER_SECONDS="${ALERT_REPEAT_AFTER_SECONDS:-21600}"  # 6h default

# After collecting issues[]:
if [ "${#issues[@]}" -gt 0 ]; then
  fingerprint="$(printf '%s\n' "${issues[@]}" | sha256sum | awk '{print $1}')"
  previous_fingerprint="$(cat "$ALERT_FINGERPRINT_FILE" 2>/dev/null || true)"
  last_sent_epoch="$(cat "$ALERT_LAST_SENT_FILE" 2>/dev/null || echo 0)"
  now_epoch="$(date -u +%s)"
  age_since_last="$(( now_epoch - last_sent_epoch ))"

  if [ "$fingerprint" != "$previous_fingerprint" ] || [ "$age_since_last" -ge "$ALERT_REPEAT_AFTER_SECONDS" ]; then
    emit_actionable_alert
    printf '%s\n' "$fingerprint" > "$ALERT_FINGERPRINT_FILE"
    printf '%s\n' "$now_epoch" > "$ALERT_LAST_SENT_FILE"
  fi
else
  # Issues resolved — clear the fingerprint so next recurrence alerts fresh
  rm -f "$ALERT_FINGERPRINT_FILE" "$ALERT_LAST_SENT_FILE"
fi
```

Logic:
- New fingerprint (different issues) → alert immediately.
- Same fingerprint but cooldown expired → re-alert (persisting issues should not go silent forever).
- Same fingerprint within cooldown → silent.
- Issues resolved → clear state, so the next recurrence of the same issue fires a fresh alert.

---

## Status file pattern

Write the full verbose status to disk every run regardless. This gives Hermes something to inspect when asked, without spamming the user:

```bash
STATUS_FILE="$STATE_DIR/last_status.txt"
{
  echo "Health check: $now_utc"
  echo "Memory: ${mem_current_mb}MB / ${mem_max_mb}MB (${mem_pct}%)"
  # ... all verbose detail ...
} > "$STATUS_FILE"

# THEN apply the alert-only output logic above
```

---

## Script-only vs agent cron jobs

| Use case | Type | Why |
|----------|------|-----|
| Health checks, data collection, file freshness | `no_agent: true` | Deterministic, fast, cheap, no LLM turn overhead |
| Summarization, briefing, analysis | Agent job (with `context_from` or script) | LLM judgment needed |
| Multi-step collection → LLM brief | Two-job pipeline | Keeps collection fast and LLM prompt focused |

For health monitors, almost always use `no_agent: true` with a shell or Python script.

---

## Cron job config fields (key ones)

```yaml
script: path/to/script.sh   # relative to /opt/data/scripts/ or absolute
no_agent: true               # script output IS the delivery; no LLM turn
deliver: telegram:<chat>:<topic>  # or "local" for disk only
schedule: "*/30 * * * *"    # 5-field cron or "every 30m" / "every 2h"
```

When reporting cron jobs to DJ, **do not show raw cron notation as the primary format.** DJ explicitly called that absurd/non-human. Translate schedules into plain English and ET-local next-run times, e.g.:

- `Runs: every 3 hours, on the hour`
- `Runs: every day at 5:00 AM ET`
- `Next run: tomorrow at 8:00 AM ET`

Only include the raw cron string if DJ asks for implementation detail or you need it for debugging.

When DJ asks how many alerts/updates to expect, count expected delivered messages under the stated assumptions, not scheduled executions. Distinguish:

- silent-on-OK monitor runs → **0 messages when healthy**
- daily summary/report jobs → **1 expected message per run**
- sync/backup jobs that print only on change → **0 if no changes, 1 if they push/report a change**
- paused jobs → **0 messages**

---

## Operational health check pattern

For monitoring several file freshness checks + script probes in Python:

```python
ISSUES: list[str] = []
LINES: list[str] = []

def check_file(path, max_age_h=None, max_size_kb=None, min_size=1):
    p = Path(path)
    if not p.exists():
        ISSUES.append(f"Missing file: {path}")
        LINES.append(f"{path}: MISSING")
        return
    age = (time.time() - p.stat().st_mtime) / 3600
    LINES.append(f"{path}: {p.stat().st_size} bytes, age {age:.1f}h")
    if p.stat().st_size < min_size:
        ISSUES.append(f"File appears empty: {path}")
    if max_age_h and age > max_age_h:
        ISSUES.append(f"Stale file: {path} age {age:.1f}h > {max_age_h}h")
```

Exit nonzero if issues found; the bash wrapper treats nonzero as issues.

---

## Hermes cron wrapper/footer control

Hermes wraps cron deliveries by default with `Cronjob Response`, `job_id`, divider, and a "To stop or manage this job..." footer. DJ flagged that footer/job metadata as extraneous for daily health-style updates. If a job's script/agent already prints the exact user-facing message, disable wrapping globally with:

```bash
/opt/hermes/.venv/bin/hermes config set cron.wrap_response false
```

Then make each cron script output its own concise self-identifying line, e.g. `Cronjob Response: <job name> successfully pushed.` or `Cronjob Response: <job name> not successful: <reason>.` This avoids raw job IDs and stop-management boilerplate in Telegram.

## Pitfalls

- **`script` is a path, not a shell command.** Do not set cron `script` to values like `foo.py weekly` or `foo.sh --flag`; Hermes resolves the whole string as a filename under `/opt/data/scripts/` and will fail with `Script not found`. Create a tiny wrapper script (`foo_weekly.sh`) that calls the underlying command with arguments, then set `script` to that wrapper path.
- **Never emit verbose output unconditionally.** Even "looks good" summaries are noise when they arrive 48 times a day.
- **Don't schedule daily jobs hourly just to handle time zones.** DJ explicitly pushed back on hourly wakeups for a once-daily Daily ToM job. For a daily local-time job with DST, prefer a narrow UTC candidate schedule (for ET 5AM: `0 9,10 * * *`) plus an in-script local-time/date guard so only one candidate performs work and the other exits silently.
- **Don't suppress logs** — write full detail to a status file so Hermes can read it on-demand; just don't push it to Telegram automatically.
- **If a user message in a Telegram topic seems to get no response, first verify whether it is a live gateway conversation vs. a cron delivery.** Cron jobs are intentionally silent on OK and may only emit output on failure; a live topic reply should come from the gateway session, not the cron runner.
- **CHIEF_HEALTH_ALWAYS_REPORT=1** can be set to force output for debugging without changing the script's default behavior.
- **Clear the fingerprint on resolution** — if you only clear it when issues appear, a persistent-then-resolved-then-recurring issue will be silenced on second occurrence.
- **Rate-limit is per-issue-fingerprint, not per-script** — different issue combinations get separate alerting behavior automatically because the fingerprint changes.

---

## References

- `references/chief-health-check-design.md` — the specific Railway Chief health check implementation and the DJ feedback that shaped this pattern.
- `references/telegram-vs-cron-replies.md` — how to tell a live Telegram topic reply from a silent cron delivery when a user says a topic is "not replying."
- `references/spend-reporting.md` — daily/weekly spend report lessons: truthful zeroes, pricing caveats, and ledger-first reporting.
