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
- **Alert only when something actionable is happening.** The output must answer: *what broke, what context do I need to understand it, and what (if anything) should DJ do?*
- **Never send a raw status block** — not memory/disk/process stats, not file ages, not check counts. Those belong in a status file written to disk for later inspection, not pushed to the user proactively.

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

## Long-running multi-step cron pipelines

Some workflows look like a single cron job on paper but are really a pipeline of independent steps (collect -> enrich -> score -> render -> deliver). If the full chain can exceed a small shell timeout, do *not* keep retrying the monolithic wrapper blindly.

Prefer one of these patterns:
- split the work into separate jobs with persisted artifacts between steps;
- run the heavy part in a background process and verify the final artifact before delivery;
- shorten the pipeline by reusing cached collection/scoring artifacts when the user only wants a recent-window digest.

Verification tip: the most useful success signal is usually the final artifact path or the delivered markdown, not just a zero exit code from the first stage.

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
