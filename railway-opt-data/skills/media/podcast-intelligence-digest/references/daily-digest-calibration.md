# DJ Podcast Daily Digest Calibration — 24h Run

Use this reference when producing DJ's daily podcast text digest after the first Qwen/OpenRouter calibration.

## Daily window

For daily digest runs, use a strict last-24-hours published window unless DJ asks otherwise.

Example window command:

```bash
date -u '+%Y-%m-%dT%H:%M:%SZ'
```

Collect with the existing prototype collector, then filter by `published >= now - 24h` before Qwen scoring. Do not accidentally score the full 7-day prototype corpus when DJ asks for today.

## Expected funnel reporting

Lead with the denominator:

- usable feeds monitored;
- episodes collected/updated;
- episodes inside strict 24h window;
- episodes scored;
- OpenRouter/Qwen cost for scoring and digest synthesis.

This directly addresses DJ's earlier complaint that a recommendation list without the filter denominator is ungrounded.

## Editorial layer after Qwen

Qwen is a retrieval/scoring assistant, not the final editor. Apply DJ's calibration before finalizing:

- `listen`: scarce; original audio likely worth DJ's time;
- `digest`: summarize in daily text; original audio optional/unnecessary;
- `scan`: maybe interesting / learn more / one-line mention;
- `skip`: omit except filtered-noise note.

Daily text can be broad, but do not let broad daily coverage inflate `listen`.

## First calibrated 24h run lessons

In the 2026-06-04 24h run, 21 strict-window episodes were scored. Qwen still over-ranked narrow AI infrastructure, technical AI research, and vertical vendor stories. The final digest manually downgraded:

- Exa/search-for-agents infrastructure promo;
- continual-learning technical research;
- Aircall/customer-service voice-agent vendor story;
- generic Bloomberg daily recap;
- Elon/SpaceX media narrative;
- consumer brand playbook;
- politics/media items.

The digest promoted or retained:

- Stratechery/Satya as best original listen;
- No Priors/Satya as optional second Satya listen;
- Dwarkesh AGI economics as listen or high-priority digest;
- Thomas Laffont/All-In AI IPO wave as summarize;
- David Solomon/Odd Lots Goldman AI as strong summarize;
- real-world evals as summarize, not listen;
- My First Million “Idiot Index” as scan/summarize because DJ had said he wanted to learn more.

## Output shape for daily text

Use markdown, no tables:

```markdown
# Daily Podcast Intelligence Digest — Last 24 Hours

**Window:** ...
**Funnel:** ...
**Model cost:** ...

## Executive read

## Listen
- What was said
- Why DJ should care
- Recommendation
- Link

## Summarize in daily digest
...

## Scan / maybe
...

## Skipped noise / filtered out
...

## Calibration note
...
```

Avoid fake links. If RSS metadata lacks a link, omit the link rather than writing placeholder text like `[no priors link]`.
