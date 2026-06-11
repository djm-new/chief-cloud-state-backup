# RSS recovery notes for podcast briefing

## What broke in this session
- The collector initially concluded there were no fresh episodes because `published` timestamps were missing/blank in the DB.
- Several active feeds were actually publishing new items; the issue was timestamp extraction, not source inactivity.
- `feedparser` did not always provide usable `published_parsed` / `updated_parsed` data for these feeds.

## Durable recovery pattern
1. Collect a feed entry's timestamp from multiple places:
   - `published_parsed` / `updated_parsed`
   - `published` / `updated`
   - RSS `pubDate`
   - alternate date-like fields if present
2. If parser output is missing timestamps, fetch the raw RSS XML and read `<pubDate>` directly.
3. Store the recovered timestamp back into the DB as UTC ISO-8601.
4. Re-check the 24h window after recollection before deciding there are no new episodes.

## Helpful verification probes
- Compare the DB’s most recent `published` rows to the live feed’s top `<item>` entries.
- If the feed has newer items but the DB does not, the collector is stale or mis-parsing.
- If the DB updates but the final digest still fails, inspect scoring/rendering separately.

## Session-specific examples
- A Libsyn feed (`https://rss.libsyn.com/shows/166112/destinations/1103966.xml`) contained fresh Naval episodes with RFC 2822 `pubDate` values.
- After raw-RSS fallback was added, the collector recovered 11 fresh items that had previously been invisible to the 24h query.
- The scoring script also hit a runtime bug where `args.since_hours` was referenced from a helper; pass runtime context explicitly into helper calls.
