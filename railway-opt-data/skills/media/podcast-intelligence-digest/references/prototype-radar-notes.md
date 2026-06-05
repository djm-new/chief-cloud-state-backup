# Prototype Radar Notes

Condensed notes from DJ's first podcast-intelligence prototype. Use as calibration context, not as a stale task log.

## Product intent

DJ wants a "global podcast conversation radar":

- daily text digest of the most important podcast conversations for him;
- weekly 15–20 minute two-host audio digest from the week's best material;
- discovery beyond subscribed shows, especially when high-signal people appear on unknown shows;
- open-source/practical models for intelligence/summarization where possible;
- high-quality TTS is a separate production decision.

## Taste profile encoded in the prototype

High signal:

- top investors/allocators and market shapers;
- scaled CEOs and operators;
- AI leaders and frontier thinkers;
- conversations that produce actions, frameworks, market reads, or mental-model shifts;
- rare-access interviews.

Low signal / skip:

- news/politics recaps;
- celebrity/entertainment;
- generic VC fluff;
- shallow founder origin stories;
- second-tier partner promo;
- energy/climate/defense/geopolitics unless user redirects.

Reference taste examples from calibration: Dwarkesh, Invest Like the Best, Conversations with Tyler, Acquired, All-In, Marc & Ben; people like Gavin Baker, Brian Chesky, Paul Tudor Jones, Stanley Druckenmiller, Ben Horowitz, Hemant Taneja, Michael Pollan, Nick Bostrom.

## Architecture that worked

Three-ring source model:

1. Ring 1: DJ subscriptions/reference shows for taste calibration.
2. Ring 2: high-signal shows likely to host relevant guests.
3. Ring 3: global guest-discovery patterns independent of show subscription.

Metadata-first, content-second:

- Resolve feeds and collect broadly.
- Rank metadata cheaply.
- Only fetch transcripts/scrape/transcribe finalists.
- Use human/LLM judgment for final curation.

## First prototype scoring lessons

The crude metadata scorer was useful for surfacing candidates, but needed calibration:

- It over-weighted AI keyword density.
- It over-counted guest/watchlist names in footer or cross-promo text.
- It under-weighted major CEO/operator/allocator conversations whose titles were less keyword-heavy.
- It needed duplicate clustering when the same interview appeared across several feeds.
- It should penalize panel/news formats harder unless the guest quality is exceptional.

Concrete example pattern: Satya Nadella appeared as a cluster across multiple feeds and should be presented as one cluster with a recommended version. David Solomon, Bill Ackman, Dara Khosrowshahi, and Dwarkesh-style AGI economics conversations are exactly the kind of candidates that need judgment beyond raw score.

## Digest format that fit the product

Use opinionated tiers:

- Must listen
- Digest only
- Skim / monitor
- Skip / deliberately excluded

Each item should answer:

- Why DJ should care
- What to listen for
- Whether full listen is worth it
- Link or best available source
- Framework/action/operator implication

Add calibration notes after prototype runs: what ranked correctly, what was noise, what to adjust.

## Audio production coupling

For weekly audio digests:

- select 3–5 strongest clusters;
- write a synthesized two-host conversation, not a list readout;
- speaker labels are production directions and must not be read aloud;
- use distinct high-quality voices where available;
- call `podcast-audio-production` for TTS/ffmpeg assembly and verification.

## Operational guardrails

- No recurring daily/weekly jobs without DJ's explicit approval.
- If sending via Telegram, digest belongs in the appropriate Briefings channel/topic, not alert-style messaging.
- Store durable source/ranking state under `/opt/data` in DJ's production environment when applicable; do not depend on `/tmp` for durable artifacts.
- X/Twitter full-thread reading may require authenticated `xurl`; public fallbacks can recover partial content/OCR but should not be treated as complete.
