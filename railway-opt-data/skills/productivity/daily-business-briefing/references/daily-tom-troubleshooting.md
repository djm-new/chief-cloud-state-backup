# Daily ToM troubleshooting notes

Use this when the Daily ToM sync/context pipeline alerts, fails a Chief health check, or DJ asks to run the ToM sync manually.

## Components

- Sync script: `/opt/data/scripts/daily-tom-sync.py`
- 5AM ET wrapper: `/opt/data/scripts/daily-tom-daily-5am-et.sh`
- Context extractor: `/opt/data/scripts/daily-tom-context.py`
- Google account wrapper: `/opt/data/scripts/google-account personal ...`
- Health probe: `/opt/data/scripts/chief_operational_health.py`

## Expected health marker

`chief_operational_health.py` expects Daily ToM context output to contain exactly:

```md
## Daily Top of Mind Context
```

If the extractor has fallback/error paths, they should emit the same marker before the error explanation. Otherwise a genuine upstream fetch failure can be misreported as a markdown-format issue.

## Manual run for today's ET date

When DJ asks to "run it for today" and side effects are explicitly intended:

```bash
TODAY="$(TZ=America/New_York date +%F)"
/opt/data/google-accounts/.venv/bin/python /opt/data/scripts/daily-tom-sync.py --date "$TODAY" --apply
/opt/data/scripts/daily-tom-context.py | sed -n '1,80p'
/opt/data/scripts/chief_operational_health.py
```

Report the JSON `status`, `date`, `latest_source_section`, counts, groups, then confirm the context extractor sees the new current section and health is OK.

## Runtime/dependency path check

The Google Workspace scripts may depend on Python Google API packages. If system `python3` lacks those packages, prefer a persistent `/opt/data` runtime instead of installing into transient/system Python:

```bash
uv venv /opt/data/google-accounts/.venv
uv pip install --python /opt/data/google-accounts/.venv/bin/python \
  google-api-python-client google-auth-oauthlib google-auth-httplib2
```

Then ensure wrappers that invoke Google APIs use `/opt/data/google-accounts/.venv/bin/python` with a `python3` fallback. This keeps the integration tied to the persistent Railway volume and avoids code changes under `/opt/hermes`.

## Schedule shape

For the Daily ToM 5AM ET job, avoid hourly cron wakeups. Use UTC candidate hours for DST plus the wrapper's ET/date guard:

```cron
0 9,10 * * *
```

The EDT candidate is 09:00 UTC; the EST candidate is 10:00 UTC. Only the matching 5AM ET candidate should do work; the other should exit silently.

## Verification checklist

- `bash -n /opt/data/scripts/daily-tom-daily-5am-et.sh`
- `/opt/data/scripts/daily-tom-context.py` starts with `## Daily Top of Mind Context`
- Context says `Current ToM section: <today's date>` after an applied run
- `/opt/data/scripts/chief_operational_health.py` ends with `Status: OK`
- `hermes cron list` shows Daily ToM enabled with schedule `0 9,10 * * *`
