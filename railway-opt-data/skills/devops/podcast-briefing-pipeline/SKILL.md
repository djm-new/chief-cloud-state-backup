---
name: podcast-briefing-pipeline
description: Operate, debug, and verify the daily/weekly podcast briefing pipeline end-to-end, including collection, semantic discovery, scoring, rendering, and cron delivery.
---

# Podcast Briefing Pipeline

Use this skill for the podcast digest/briefing system when the user wants the daily podcast briefing to *actually ship*, or when the pipeline appears empty, stale, timed out, or partially broken.

This is a **pipeline skill**, not a one-off incident log: the goal is to preserve the operating model for future runs while keeping transient session details in `references/`.

## Core intent
- Preserve the intended design: broad collection, semantic discovery, then bounded scoring/rendering.
- Treat the 24h window as a *signal*, not a conclusion. If it looks empty, verify the collector before assuming there were no new episodes.
- Optimize for a final artifact that can be delivered, not for a perfectly “clean” intermediate run.

## Default workflow
1. **Check the latest artifacts first**
   - Review the newest run log, semantic discovery output, and final rendered markdown if present.
   - If there is no final digest, determine whether the failure happened in collection, scoring, or rendering.

2. **Verify freshness from the database, not just the wrapper output**
   - Inspect the episode DB for the newest `published` rows and the count of rows in the last 24h.
   - If the DB looks stale but live feeds are fresh, suspect parsing/collection rather than “no episodes published.”

3. **Validate collection before diagnosing ranking**
   - Re-run the collector if needed.
   - Compare raw feed timestamps with stored `published` values.
   - If feed entries exist but `published` is blank, fix the parser path before touching scoring.

4. **Keep semantic discovery bounded, not removed**
   - Semantic discovery can stay in the daily path, but it should be time-bounded so the cron job still finishes.
   - If discovery adds no candidates, that is acceptable; if it causes the run to miss its window, tighten the bound rather than disabling it permanently.

5. **Only then run scoring/rendering**
   - If the collector actually found fresh episodes, run episode scoring and rendering to produce the final markdown artifact.
   - If scoring fails, inspect the caller/callee boundary and any metadata fields that reference parsed CLI args or runtime context.

6. **Deliver the artifact**
   - Confirm the final digest path exists.
   - For Telegram delivery, strip hidden metadata comments only at the delivery boundary, not in the source artifact.

## Common pitfalls
- **Blank `published` does not mean no new podcasts.**
  - Some podcast feeds expose fresh RSS items whose timestamps are only visible in the raw XML or alternate fields.
  - If `feedparser` yields entries without usable timestamps, parse the raw feed XML as a fallback.

- **Do not stop at stale DB conclusions.**
  - If the episode DB appears unchanged, verify whether the collector is failing to populate timestamps before assuming the source feeds are stale.

- **404s are usually feed hygiene issues, not pipeline failure.**
  - Log stale feed URLs, but don’t let a couple of broken feeds invalidate the whole run.

- **Score-script runtime context can break in metadata plumbing.**
  - If a scoring helper references CLI args from inside a nested function, pass the needed values explicitly.

- **Cron timeout must be controlled at the scheduler/config layer.**
  - Wrapper-level timeouts help, but the scheduler’s script timeout still needs enough headroom for the full path.

## Verification checklist
- Latest run log exists and shows collection completed.
- Episode DB has fresh rows with non-empty `published` timestamps when fresh feeds exist.
- Semantic discovery output exists and completed within the budget.
- Scoring JSON and final markdown are generated when the window has candidates.
- The final artifact path is visible and matches the rendered digest naming convention.

## Deliverables and conventions
- Prefer current-state-first explanations: what is the latest verified artifact, what changed, and what still blocks delivery.
- Use America/New_York for user-facing time references unless asked otherwise.
- Be explicit about whether the issue is:
  - no fresh episodes,
  - collector/parsing failure,
  - scoring/rendering failure,
  - or cron/timeout failure.

## See also
- `references/rss-recovery.md` for the feed parsing / blank-published recovery pattern and the June 10 troubleshooting notes.
- This skill overlaps with generic cron-job and debugging workflows; prefer this skill when the task is specifically about the podcast briefing pipeline.
