#!/usr/bin/env bash
set -euo pipefail

BASE="/opt/data/podcast_digest"
OUTDIR="$BASE/outputs"
mkdir -p "$OUTDIR"

# Run the production-ish daily podcast radar pipeline for DJ.
# Output discipline: if successful, print the final digest only; if a step fails, exit nonzero so cron sends an error.

export PYTHONUNBUFFERED=1
export PODCAST_SCORE_BATCH_SIZE="${PODCAST_SCORE_BATCH_SIZE:-10}"

log="$OUTDIR/$(date -u +%Y-%m-%d_%H%M)-podcast-digest-run.log"

{
  echo "Podcast digest run started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Step 1: collect known feeds"
  python3 /opt/data/scripts/podcast_resolve_collect_rank.py collect --days 1
  echo "Step 2: semantic discovery"
  python3 /opt/data/scripts/podcast_semantic_discovery.py --days 1
  echo "Step 3: Qwen episode scoring"
  python3 /opt/data/scripts/podcast_qwen_episode_score.py --since-hours 24 --tag daily-24h
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
python3 /opt/data/scripts/podcast_daily_digest_qwen.py "$scores_json" \
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
