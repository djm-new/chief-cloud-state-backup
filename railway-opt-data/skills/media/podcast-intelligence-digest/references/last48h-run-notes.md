# Last 48h digest run notes (June 2026)

## What happened
- A two-day digest run was built from the existing prototype corpus in `/opt/data/podcast_digest/episodes.sqlite`.
- The data store currently spans roughly 2026-05-28 through 2026-06-05.
- The last-48h scoring pass produced a compact calibration set and a rendered digest successfully.

## Key operational details
- Use the Hermes venv interpreter for durable execution of the prototype scripts:
  - `/opt/hermes/.venv/bin/python3 /opt/data/scripts/podcast_resolve_collect_rank.py ...`
  - `/opt/hermes/.venv/bin/python3 /opt/data/scripts/podcast_qwen_episode_score.py ...`
  - `/opt/hermes/.venv/bin/python3 /opt/data/scripts/podcast_daily_digest_qwen.py ...`
- The prototype scripts may not run cleanly under the system Python when invoked from ad hoc shell commands.
- The scoring job prints `JSON=...` and `MD=...` lines; the digest renderer prints the output path as its last line.
- For quick ad hoc runs, scoring 23 episodes used about 9.8k tokens and ~$0.007 in OpenRouter cost.

## Digest shape that worked
- Title: `Daily Podcast Intelligence Digest — Last 24 Hours`
- Funnel line up top: `N episodes -> digest/scan/skip counts`
- Sections:
  - Executive Read
  - Listen
  - Summarize in Digest
  - Scan / Maybe
  - Skipped Noise
- The rendered digest should stay concise and opinionated, with no tables and no placeholder links.

## Pitfalls discovered
- A monolithic shell wrapper with collect + semantic discovery + scoring + render can exceed the platform's default 120s timeout.
- If you need a user-visible digest, prefer either:
  1. running the pieces separately with persisted artifacts, or
  2. running the full pipeline in a background process and checking for the final markdown artifact.
- If collection fails immediately, check the interpreter first before debugging the podcast logic itself.
- The raw prototype scoring files are ephemeral; the durable knowledge is the calibration pattern and the output shape, not the generated artifact itself.
