# Podcast briefing pipeline notes

This reference condenses the former `podcast-briefing-pipeline` sibling into operating notes for `podcast-intelligence-digest`.

## Operating model
- Preserve the intended sequence: collect broadly, run bounded semantic discovery, score/render, then deliver.
- Treat an empty-looking 24h window as a signal to verify the collector and database before assuming nothing was published.
- Optimize for a shippable final digest, not for perfect intermediate cleanliness.

## Debug order
1. Inspect the newest run log, semantic discovery output, and final markdown artifact.
2. Verify episode freshness directly in the database.
3. Re-run or inspect collection before changing ranking logic.
4. Keep semantic discovery time-bounded so the job still finishes.
5. Then run scoring/rendering and verify the final path exists.

## Common pitfalls
- Some feeds expose fresh items only through raw RSS `pubDate`; blank parsed timestamps do not necessarily mean no new episodes.
- A stale episode DB may point to collector/parsing issues rather than stale feeds.
- 404s are usually feed hygiene problems.
- Runtime context bugs can happen when scoring helpers depend on nested CLI state.
- If a wrapper hits cron limits, raise the scheduler budget and bound internal stages instead of removing intended work.

## Delivery conventions
- Explain the current verified artifact first.
- State clearly whether the failure is collection, scoring/rendering, or cron/timeout related.
- Use America/New_York for user-facing time references unless asked otherwise.
