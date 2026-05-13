---
name: chief-health-report
description: "On-demand Railway Chief health report: memory, disk, gateway, backup status."
version: 1.0.0
author: DJ Mauch
platforms: [gateway]
metadata:
  hermes:
    tags: [health, monitoring, railway, memory, disk, status, chief]
---

# Chief Health Report

Load this skill when the user asks anything like:

- "how are you doing"
- "health check"
- "are you ok"
- "status"
- "memory usage"
- "how's your memory"
- "are you running low on memory"
- "system status"
- "railway status"
- "how much disk"

## What to do

Run the health check script and report the results to the user in plain, friendly English via Telegram.

Use terminal to run:

```bash
CHIEF_HEALTH_ALWAYS_REPORT=1 /opt/data/scripts/chief_health_check.sh
```

Parse the output and reply with a short human-readable summary. Do not paste raw script output. Translate the numbers into something useful.

## Response format

Keep it short. One short paragraph or a few bullet points. Example good response:

"All good here. I'm using 315 MB of memory out of about 22 GB available — barely a dent. The Railway volume has 38 MB used out of 46 GB. Gateway is running and both Telegram and Slack are connected. Last backup ran this morning."

If there are issues, be clear and specific:

"Heads up — memory is at 82% (18.7 GB of 22 GB). That's getting tight. You may want to restart the Railway service before it causes problems."

## Important context

- Memory limit: Railway container cgroup limit, read from `/sys/fs/cgroup/memory.max`
- Disk: Railway persistent volume mounted at `/opt/data`
- The 30-minute automatic health alert cron is separate — it only fires when something is wrong
- This skill is for when you ask directly

## Backup status

If the user asks specifically about backup status, also check:

```bash
cat /opt/data/health/last_status.txt
cat /opt/data/github/chief-cloud-state-backup/.git/logs/HEAD 2>/dev/null | tail -3
```

Tell them when the last backup ran and whether it succeeded.
