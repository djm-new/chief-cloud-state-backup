#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/opt/data/health"
STATUS_FILE="$STATE_DIR/last_status.txt"
ALERT_FINGERPRINT_FILE="$STATE_DIR/last_alert_fingerprint.txt"
ALERT_LAST_SENT_FILE="$STATE_DIR/last_alert_sent_at"
ALERT_REPEAT_AFTER_SECONDS="${CHIEF_HEALTH_REPEAT_ALERT_AFTER_SECONDS:-21600}"
mkdir -p "$STATE_DIR"

now_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
issues=()
dj_action_required=0

read_int_file() {
  local path="$1"
  if [ -f "$path" ]; then
    cat "$path" 2>/dev/null || echo 0
  else
    echo 0
  fi
}

mem_current="$(read_int_file /sys/fs/cgroup/memory.current)"
mem_max="$(read_int_file /sys/fs/cgroup/memory.max)"
if [ "$mem_max" = "max" ] || [ -z "$mem_max" ] || [ "$mem_max" = "0" ]; then
  mem_pct="unknown"
else
  mem_pct="$(( mem_current * 100 / mem_max ))"
fi
mem_current_mb="$(( mem_current / 1024 / 1024 ))"
if [ "$mem_pct" = "unknown" ]; then
  mem_max_mb="unknown"
else
  mem_max_mb="$(( mem_max / 1024 / 1024 ))"
fi

if [ "$mem_pct" != "unknown" ] && [ "$mem_pct" -ge 80 ]; then
  issues+=("Memory is high: ${mem_current_mb}MB / ${mem_max_mb}MB (${mem_pct}%).")
  dj_action_required=1
fi

disk_line="$(df -Pm /opt/data | awk 'NR==2 {print $3 " " $2 " " $5}')"
disk_used_mb="$(printf '%s' "$disk_line" | awk '{print $1}')"
disk_total_mb="$(printf '%s' "$disk_line" | awk '{print $2}')"
disk_pct="$(printf '%s' "$disk_line" | awk '{gsub(/%/,"",$3); print $3}')"
if [ -n "${disk_pct:-}" ] && [ "$disk_pct" -ge 85 ]; then
  issues+=("Railway volume disk usage is high: ${disk_used_mb}MB / ${disk_total_mb}MB (${disk_pct}%).")
  dj_action_required=1
fi

if ! pgrep -af 'hermes gateway run' >/dev/null 2>&1; then
  issues+=("Could not find a running 'hermes gateway run' process.")
  dj_action_required=1
fi

operational_health=""
operational_issues=""
if [ -x /opt/data/scripts/chief_operational_health.py ]; then
  if ! operational_health="$(/opt/data/scripts/chief_operational_health.py 2>&1)"; then
    operational_issues="$(printf '%s\n' "$operational_health" | grep '^Issue:' | sed 's/^Issue: //')"
    if [ -n "$operational_issues" ]; then
      while IFS= read -r issue; do
        [ -n "$issue" ] && issues+=("$issue")
      done <<EOF
$operational_issues
EOF
      dj_action_required=1
    else
      issues+=("Chief operational health checks found issues.")
      dj_action_required=1
    fi
  fi
fi

recent_errors=""
if [ -f /opt/data/logs/gateway.log ]; then
  recent_errors="$(tail -300 /opt/data/logs/gateway.log \
    | grep -Ei '^[0-9-]+ [0-9:,]+ (ERROR|CRITICAL) |Traceback|OutOfMemory|killed process' \
    | awk '
        /Another gateway instance \(PID 1\) started during our startup\. Exiting to avoid double-running\./ { next }
        /slash-confirm callback failed:/ && index($0, "Can\047t parse entities: can\047t find end of the entity starting at byte offset") { skip_tb=1; next }
        skip_tb && /^Traceback \(most recent call last\):$/ { skip_tb=0; next }
        skip_tb { next }
        { print }
      ' \
    | tail -10 || true)"
  if [ -n "$recent_errors" ]; then
    issues+=("Recent severe gateway log lines were found.")
    dj_action_required=1
  fi
fi

{
  echo "Chief Railway health check: $now_utc"
  echo "Memory: ${mem_current_mb}MB / ${mem_max_mb}MB (${mem_pct}%)"
  echo "Railway volume disk: ${disk_used_mb}MB / ${disk_total_mb}MB (${disk_pct}%)"
  echo "Gateway process: $(pgrep -af 'hermes gateway run' | head -1 || echo missing)"
  if [ -n "$operational_health" ]; then
    echo "Operational checks:"
    printf '%s\n' "$operational_health" | sed 's/^/  /'
  fi
  if [ "${#issues[@]}" -eq 0 ]; then
    echo "Status: OK"
  elif [ "$dj_action_required" -eq 1 ]; then
    echo "Status: DJ ACTION NEEDED"
    printf 'Issue: %s\n' "${issues[@]}"
    if [ -n "$recent_errors" ]; then
      echo "Recent severe log tail:"
      printf '%s\n' "$recent_errors"
    fi
  else
    echo "Status: HERMES FOLLOW-UP"
    printf 'Issue: %s\n' "${issues[@]}"
  fi
} > "$STATUS_FILE"

action_for_issue() {
  case "$1" in
    "Memory is high:"*)
      echo "Reduce memory use or restart the largest memory-hungry process."
      ;;
    "Railway volume disk usage is high:"*)
      echo "Free disk space under /opt/data by pruning old logs, caches, or artifacts."
      ;;
    "Could not find a running 'hermes gateway run' process."*)
      echo "Restart the Hermes gateway process."
      ;;
    "Recent severe gateway log lines were found."*)
      echo "Open /opt/data/logs/gateway.log and inspect the matching ERROR/CRITICAL lines."
      ;;
    "Missing file:"*)
      echo "Create or restore the missing file named above."
      ;;
    "File appears empty:"*)
      echo "Regenerate the empty file named above."
      ;;
    "Stale file:"*)
      echo "Regenerate or refresh the stale file named above."
      ;;
    "Hot file too large:"*)
      echo "Trim, archive, or rotate the oversized file named above."
      ;;
    "* failed:"*)
      echo "Run the named check again and fix the underlying failure it reports."
      ;;
    *)
      echo "Inspect the issue details above and fix the named problem."
      ;;
  esac
}

emit_actionable_alert() {
  if [ "${#issues[@]}" -eq 0 ]; then
    echo "✅ Chief OK"
    echo "Time: $now_utc"
    echo "Memory: ${mem_current_mb}MB / ${mem_max_mb}MB (${mem_pct}%)"
    echo "Railway volume: ${disk_used_mb}MB / ${disk_total_mb}MB (${disk_pct}%)"
    echo "DJ action: none."
    return
  fi

  echo "⚠️ Chief needs DJ attention"
  echo "Time: $now_utc"
  echo ""
  echo "What changed:"
  printf -- '- %s\n' "${issues[@]}"
  echo ""
  echo "Useful context:"
  echo "- Memory: ${mem_current_mb}MB / ${mem_max_mb}MB (${mem_pct}%)"
  echo "- Railway volume: ${disk_used_mb}MB / ${disk_total_mb}MB (${disk_pct}%)"
  if [ -n "$recent_errors" ]; then
    echo ""
    echo "Recent severe gateway log lines:"
    printf '%s\n' "$recent_errors"
  fi
  if [ -n "$operational_health" ]; then
    operational_issues="$(printf '%s\n' "$operational_health" | grep '^Issue:' || true)"
    if [ -n "$operational_issues" ]; then
      echo ""
      echo "Operational issue details:"
      printf '%s\n' "$operational_issues" | sed 's/^Issue: /- /'
    fi
  fi
  echo ""
  echo "DJ action:"
  for issue in "${issues[@]}"; do
    action="$(action_for_issue "$issue")"
    if [ -n "$action" ]; then
      printf -- '- %s\n' "$action"
    fi
  done
}

if [ "${CHIEF_HEALTH_ALWAYS_REPORT:-0}" = "1" ]; then
  emit_actionable_alert
  exit 0
fi

if [ "${#issues[@]}" -gt 0 ] && [ "$dj_action_required" -eq 1 ]; then
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
  rm -f "$ALERT_FINGERPRINT_FILE" "$ALERT_LAST_SENT_FILE"
fi
