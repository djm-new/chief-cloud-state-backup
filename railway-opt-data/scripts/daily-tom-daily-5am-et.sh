#!/usr/bin/env bash
set -euo pipefail

# Run Daily ToM sync exactly once per America/New_York calendar day at 5AM.
# This wrapper is safe to schedule hourly in UTC; it stays silent outside 5AM ET.

export TZ=America/New_York
now_hour="$(date +%H)"
today="$(date +%F)"
state_dir="/opt/data/daily-tom"
last_run_file="$state_dir/last_5am_et_run_date"
mkdir -p "$state_dir"

if [[ "$now_hour" != "05" ]]; then
  exit 0
fi

if [[ -f "$last_run_file" && "$(cat "$last_run_file")" == "$today" ]]; then
  exit 0
fi

out="$(/opt/data/scripts/daily-tom-sync.py --date "$today" --apply)"
printf '%s' "$today" > "$last_run_file"
chmod 600 "$last_run_file"

python3 - <<'PY' <<<"$out"
import json, sys
j=json.load(sys.stdin)
if j.get('status') == 'noop':
    print(f"Daily ToM sync: no-op for {j.get('date')} — {j.get('reason')}")
else:
    c=j.get('counts', {})
    bg=j.get('by_group', {})
    print(
        "Daily ToM sync complete\n"
        f"Date: {j.get('date')}\n"
        f"Source: {j.get('latest_source_section')}\n"
        f"Carried: {c.get('carried', 0)} tasks\n"
        f"Slack added: {c.get('slack_added', 0)} tasks\n"
        f"Returning from parking: {c.get('returning_from_parking', 0)}\n"
        f"Completed skipped: {c.get('completed_seen', 0)}\n"
        f"Groups: Professional {bg.get('Professional', 0)} / MENA {bg.get('Professional - MENA', 0)} / Others {bg.get('Professional - Others', 0)} / Personal {bg.get('Personal', 0)}"
    )
PY
