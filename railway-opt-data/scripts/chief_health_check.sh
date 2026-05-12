#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/opt/data/health"
STATUS_FILE="$STATE_DIR/last_status.txt"
mkdir -p "$STATE_DIR"

now_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
issues=()

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
fi

disk_line="$(df -Pm /opt/data | awk 'NR==2 {print $3 " " $2 " " $5}')"
disk_used_mb="$(printf '%s' "$disk_line" | awk '{print $1}')"
disk_total_mb="$(printf '%s' "$disk_line" | awk '{print $2}')"
disk_pct="$(printf '%s' "$disk_line" | awk '{gsub(/%/,"",$3); print $3}')"
if [ -n "${disk_pct:-}" ] && [ "$disk_pct" -ge 85 ]; then
  issues+=("Railway volume disk usage is high: ${disk_used_mb}MB / ${disk_total_mb}MB (${disk_pct}%).")
fi

if ! pgrep -af 'hermes gateway run' >/dev/null 2>&1; then
  issues+=("Could not find a running 'hermes gateway run' process.")
fi

recent_errors=""
if [ -f /opt/data/logs/gateway.log ]; then
  recent_errors="$(tail -300 /opt/data/logs/gateway.log | grep -Ei '^[0-9-]+ [0-9:,]+ (ERROR|CRITICAL) |Traceback|OutOfMemory|killed process' | tail -10 || true)"
  if [ -n "$recent_errors" ]; then
    issues+=("Recent severe gateway log lines were found.")
  fi
fi

{
  echo "Chief Railway health check: $now_utc"
  echo "Memory: ${mem_current_mb}MB / ${mem_max_mb}MB (${mem_pct}%)"
  echo "Railway volume disk: ${disk_used_mb}MB / ${disk_total_mb}MB (${disk_pct}%)"
  echo "Gateway process: $(pgrep -af 'hermes gateway run' | head -1 || echo missing)"
  if [ "${#issues[@]}" -eq 0 ]; then
    echo "Status: OK"
  else
    echo "Status: ATTENTION NEEDED"
    printf 'Issue: %s\n' "${issues[@]}"
    if [ -n "$recent_errors" ]; then
      echo "Recent severe log tail:"
      printf '%s\n' "$recent_errors"
    fi
  fi
} > "$STATUS_FILE"

if [ "${CHIEF_HEALTH_ALWAYS_REPORT:-0}" = "1" ]; then
  cat "$STATUS_FILE"
  exit 0
fi

if [ "${#issues[@]}" -gt 0 ]; then
  cat "$STATUS_FILE"
fi
