# Railway Chief Health Check — Design Notes

## DJ feedback (2026-05-27)

The original `chief_health_check.sh` output on every tick:

```
Chief Railway health check: 2026-05-26T20:30:53Z
Memory: 993MB / 22888MB (4%)
Railway volume disk: 156MB / 46627MB (1%)
Gateway process: 1 /opt/hermes/.venv/bin/python3 /opt/hermes/.venv/bin/hermes gateway run
Operational checks:
  Chief operational health: 2026-05-26T20:30:58.068904+00:00
  Check: /opt/data/daily-tom/task_state.json: 5446 bytes, age 5.4h
  ...
  Status: OK
Status: OK
```

DJ said: **"this is entirely useless to me. the format or the output needs to change."**

## What changed

Rewrote output logic in `chief_health_check.sh`:

1. **Silent on OK.** Script produces no stdout when everything is fine → cron delivers nothing.
2. **Alert-only output** when issues exist, structured as:
   - emoji flag + "needs attention"
   - What changed (issues list)
   - Useful context (metrics)
   - Severe log tail (if present)
   - Operational issue details extracted from Python checker
   - DJ action line
3. **Dedup + rate-limit:** fingerprint of issue set stored at `/opt/data/health/last_alert_fingerprint.txt`; timestamp at `last_alert_sent_at`. Re-alerts only on new fingerprint or after 6h cooldown. State cleared on clean run.
4. **Status file still written every run** to `/opt/data/health/last_status.txt` — full verbose detail available for on-demand inspection.

## Files

- `/opt/data/scripts/chief_health_check.sh` — bash wrapper (alert logic, metrics)
- `/opt/data/scripts/chief_operational_health.py` — Python checker (file freshness, script probes)
- `/opt/data/health/last_status.txt` — full verbose status (written every run)
- `/opt/data/health/last_alert_fingerprint.txt` — dedup fingerprint
- `/opt/data/health/last_alert_sent_at` — epoch of last sent alert

## Cron job

- ID: `6fd3f691efe5`
- Schedule: `*/30 * * * *`
- Delivery: `telegram:-1003956828149:5` (alerts topic)
- Type: `no_agent: true`, script only
