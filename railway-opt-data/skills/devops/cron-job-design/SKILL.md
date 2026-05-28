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

When there IS something wrong, the alert message should be:

```
⚠️ <System> needs attention
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

DJ action: <either "none unless this repeats" or specific action required>
```

Key rules:
- Lead with emoji flag so it's scannable in Telegram.
- "What changed" = the issues list, bullet-formatted.
- "Useful context" = metrics only when the issue could be caused by resource pressure.
- "DJ action" = either "none, Hermes should fix this" or an explicit ask. Never omit this line.

---

## Alert dedup / rate-limiting pattern

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

## Pitfalls

- **Never emit verbose output unconditionally.** Even "looks good" summaries are noise when they arrive 48 times a day.
- **Don't suppress logs** — write full detail to a status file so Hermes can read it on-demand; just don't push it to Telegram automatically.
- **CHIEF_HEALTH_ALWAYS_REPORT=1** can be set to force output for debugging without changing the script's default behavior.
- **Clear the fingerprint on resolution** — if you only clear it when issues appear, a persistent-then-resolved-then-recurring issue will be silenced on second occurrence.
- **Rate-limit is per-issue-fingerprint, not per-script** — different issue combinations get separate alerting behavior automatically because the fingerprint changes.

---

## References

- `references/chief-health-check-design.md` — the specific Railway Chief health check implementation and the DJ feedback that shaped this pattern.
