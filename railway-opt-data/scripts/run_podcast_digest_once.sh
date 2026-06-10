#!/usr/bin/env bash
set -euo pipefail

BASE="/opt/data/podcast_digest"
OUTDIR="$BASE/outputs"
mkdir -p "$OUTDIR"

# Run the production-ish daily podcast radar pipeline for DJ.
# Output discipline: if successful, print the final digest only; if a step fails, exit nonzero so cron sends an error.

export PYTHONUNBUFFERED=1
export PODCAST_SCORE_BATCH_SIZE="${PODCAST_SCORE_BATCH_SIZE:-20}"
export PODCAST_RUN_SEMANTIC_DISCOVERY="${PODCAST_RUN_SEMANTIC_DISCOVERY:-0}"
export PODCAST_COLLECT_TIMEOUT_SECONDS="${PODCAST_COLLECT_TIMEOUT_SECONDS:-90}"
PY="${PY:-/opt/hermes/.venv/bin/python3}"

# Daily 5PM ET guard: cron fires on UTC candidate hours 21/22, but only the
# 5PM America/New_York candidate should actually do work.
if [[ "$(TZ=America/New_York date +%H)" != "17" ]]; then
  exit 0
fi

log="$OUTDIR/$(date -u +%Y-%m-%d_%H%M)-podcast-digest-run.log"

{
  echo "Podcast digest run started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Step 1: collect known feeds"
  if ! timeout "$PODCAST_COLLECT_TIMEOUT_SECONDS" "$PY" /opt/data/scripts/podcast_resolve_collect_rank.py collect --days 1; then
    echo "Step 1 note: collection hit the time budget; continuing with cached episodes."
  fi
  if [[ "$PODCAST_RUN_SEMANTIC_DISCOVERY" == "1" ]]; then
    echo "Step 2: semantic discovery"
    if ! timeout 20s "$PY" /opt/data/scripts/podcast_semantic_discovery.py --days 1; then
      echo "Step 2 note: semantic discovery skipped or timed out."
    fi
  else
    echo "Step 2: semantic discovery skipped (set PODCAST_RUN_SEMANTIC_DISCOVERY=1 to enable)"
  fi
  episode_count="$($PY - <<'PY'
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
DB = Path('/opt/data/podcast_digest/episodes.sqlite')
con = sqlite3.connect(DB)
since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
count = con.execute('select count(*) from episodes where published >= ?', (since,)).fetchone()[0]
print(count)
PY
)"
  if [[ "$episode_count" -eq 0 ]]; then
    exit 0
  fi
  echo "Step 3: Qwen episode scoring"
  "$PY" /opt/data/scripts/podcast_qwen_episode_score.py --since-hours 24 --tag daily-24h
} > "$log" 2>&1

scores_json="$(grep '^JSON=' "$log" | tail -1 | sed 's/^JSON=//')"
if [[ -z "${scores_json:-}" || ! -f "$scores_json" ]]; then
  echo "⚠️ Podcast digest failed"
  echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "What changed: scoring completed without a JSON output path."
  echo "Log: $log"
  exit 1
fi

digest_log="$OUTDIR/$(date -u +%Y-%m-%d_%H%M)-podcast-digest-render.log"
"$PY" /opt/data/scripts/podcast_daily_digest_qwen.py "$scores_json" \
  --window-start "$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --window-end "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$digest_log" 2>&1

digest_path="$(grep '^/opt/data/podcast_digest/outputs/.*daily-podcast-digest-24h\.md$' "$digest_log" | tail -1)"
if [[ -z "${digest_path:-}" || ! -f "$digest_path" ]]; then
  echo "⚠️ Podcast digest failed"
  echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "What changed: digest rendering completed without a digest markdown path."
  echo "Scoring JSON: $scores_json"
  echo "Run log: $log"
  echo "Render log: $digest_log"
  exit 1
fi

# Strip hidden HTML metadata comment before Telegram delivery.
sed '/^<!-- model=/d' "$digest_path"
printf '\n\nGenerated: %s\nArtifact: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$digest_path"
