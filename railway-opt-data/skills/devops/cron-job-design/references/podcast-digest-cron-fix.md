# Podcast digest cron fix

This reference captures the durable lessons from fixing the podcast digest pipeline.

## Root causes
- Some podcast feeds exposed fresh episodes only through raw RSS `pubDate` strings, while `feedparser` left `published` empty.
- The daily wrapper treated an empty 24h window as absence of new content, so it exited before scoring/rendering.
- The digest renderer was hard-coded to `24h`, which made longer-window runs awkward to label and verify.

## Fix pattern
1. Parse `pubDate` / RFC 2822 from the raw RSS as a fallback when parsed dates are missing.
2. Keep the normal ET guard, but allow a manual bypass flag for verification.
3. Preserve semantic discovery in the daily path, but bound it with a timeout instead of removing it.
4. Use window-aware scoring/rendering tags (`72h`, `24h`, etc.) so output filenames and headings reflect the actual run.
5. Save both artifacts: the scored JSON and the final rendered markdown.

## Verification checklist
- Collector run shows nonzero `collected_or_updated` for fresh feeds.
- Latest episodes in the DB have valid `published` timestamps.
- Scoring JSON exists for the requested window.
- Final digest markdown exists and its header matches the requested window.
- The digest includes the expected sections: Executive read, Listen, Summarize in digest, Scan / maybe, Skipped noise.

## Common pitfall
If the 24h window looks empty, verify raw feed dates before assuming there was no new content. The collector may be missing items because the parser did not populate `published`.