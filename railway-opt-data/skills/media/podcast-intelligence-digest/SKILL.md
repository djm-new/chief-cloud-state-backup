---
name: podcast-intelligence-digest
description: "Build, run, calibrate, and automate DJ's podcast conversation radar: global podcast discovery, episode ranking, daily text digests, and weekly audio briefings."
version: 1.0.0
author: Hermes Agent
license: private
metadata:
  hermes:
    tags: [podcasts, digest, briefing, discovery, rss, ranking, audio-briefing]
    related_skills: [youtube-content, daily-business-briefing]
---

# Podcast Intelligence Digest

## Overview

Use this skill for DJ's "global podcast conversation radar": identifying the highest-signal podcast conversations from a broad source universe, ranking them against DJ's intellectual/professional taste, producing a concise daily text digest, and optionally turning the week's best conversations into a two-host audio digest.

The product is **not** a generic podcast newsletter. It should behave like a sharp analyst scanning the podcast world for conversations DJ would actually act on, listen to, or use to update a mental model.

## Daily vs weekly distinction:
- the daily text digest should cast a wider net and summarize what was said across more potentially relevant episodes.
- the weekly "podcast of podcasts" audio should be much more finely tuned: only the highest-signal, DJ-specific themes/conversations should make it into the script.

**Storage principle:** persist learnings, not artifacts. Keep durable taste calibration, final labels, and an idea index; do not keep raw daily Qwen JSON, calibration markdown, transcripts, or scratch files forever. Daily outputs should be delivered as iPhone-friendly plain text and optionally kept only in a short rolling archive.

## Pipeline operations and delivery triage

Use the pipeline-specific notes when a podcast digest run is empty, stale, timed out, or partially broken. The goal is to preserve the intended workflow without turning transient incidents into permanent top-level skills.

### Diagnose in the right order
1. Check the latest run log, semantic discovery output, and rendered markdown first.
2. Verify freshness from the episode DB, not only the wrapper output.
3. Validate collection before blaming ranking.
4. Keep semantic discovery bounded rather than removing it.
5. Only then run scoring/rendering.
6. Confirm the final artifact path exists before delivery.

### Common failure modes
- Blank `published` timestamps can hide fresh episodes; fall back to raw RSS XML parsing before declaring the window empty.
- A stale DB does not prove stale feeds; it may indicate a parser/collector problem.
- 404s usually mean feed hygiene issues, not a pipeline-wide outage.
- Scoring helpers can break on metadata plumbing if runtime context is passed implicitly instead of explicitly.
- Cron timeouts should be solved with scheduler budget plus bounded internal steps, not by deleting intended work.

### Delivery conventions
- Prefer current-state-first explanations: what is the latest verified artifact, what changed, and what still blocks delivery.
- Be explicit about whether the issue is no fresh episodes, collector/parsing failure, scoring/rendering failure, or cron/timeout failure.
- For user-facing times, default to America/New_York unless asked otherwise.

### See also
- `references/rss-recovery.md` for the feed parsing and blank-published recovery pattern.
- `references/podcast-briefing-pipeline.md` for the condensed incident-to-operating-model notes absorbed from the former sibling skill.

**Calibration from DJ's first Qwen episode pass:** Qwen's first pass was too generous with `listen`. Treat `listen` as scarce original-audio-worthy, `digest` as worth summarizing, `scan` as investigate/brief mention, `skip` as omit. DJ explicitly liked/listened to: Benedict Evans appearances/rational AI economics, Mercor CEO on AI labor/model economics, Dara/Uber AV strategy, Gita Gopinath global rates, Ranjan Roy on AI boom warnings, Toast business breakdown, and Stratechery best-of content. DJ wanted summaries for enterprise data infrastructure/Fivetran agents, Axiom Math, operator-led PE, RenMac market models, Mark Pincus product frameworks, evolutionary AI models, personal AI workflows, Terry Sejnowski, and China vs Nvidia. DJ skipped high-scoring but too-narrow/noisy items like Exa search infra promo, continual-learning research, video/generative-media agent demos, generic AI consciousness/alarmism, vertical AI vendor stories, Corgi culture promo, Elon/media narrative, consumer brand playbooks, crypto chatter, and generic Bloomberg/news recaps.

## When to Use

Use when the user asks to:

- build, run, debug, or calibrate a podcast digest/radar/monitor;
- collect podcast episodes from RSS feeds;
- rank episodes by guest/topic relevance;
- produce a daily podcast intelligence brief;
- script or generate a weekly audio digest from podcast highlights;
- expand discovery beyond subscribed shows by searching for high-signal guests.

If the task is purely converting an already-written script into audio, use `podcast-audio-production` instead. If podcast audio generation is part of a weekly digest pipeline, use this skill first for selection/scripting, then `podcast-audio-production` for production.

## DJ Relevance Test

Every candidate episode must pass this question:

> Will this conversation give DJ an action, framework, market read, operator insight, allocation implication, or mental-model shift?

**Context-sensitive framing:** if an episode touches Flow, Adam Neumann, or another entity DJ owns/operates closely, surface that relationship explicitly in the recommendation. Do not present it like a generic third-party podcast when it is actually about DJ's company or day-to-day leadership surface.

Prioritize:

- market/business shapers;
- top investors, allocators, and CEOs;
- AI leaders and frontier thinkers;
- rare-access conversations with decision-makers;
- operator details from scaled companies;
- durable frameworks, not news chatter;
- business model, capital allocation, software economics, AI platform, labor/productivity, and company-building implications.

Penalize or skip:

- news recaps and politics-first commentary;
- celebrity/entertainment interviews;
- generic VC/promotional fluff;
- second-tier partner promo episodes;
- shallow founder origin stories without reusable ideas;
- generic AI hype with no operator/investor specificity;
- energy/climate/defense/geopolitics unless DJ explicitly redirects the product.

## Source Model

Maintain a three-ring source universe:

1. **Ring 1 — calibration subscriptions**: shows DJ already values. Use these to understand taste and baseline signal.
2. **Ring 2 — high-signal shows**: shows likely to host relevant CEOs, investors, AI leaders, and framework thinkers.
3. **Ring 3 — semantic global discovery**: do not rely only on known shows, exact guest watchlists, or exact topic keywords. Use DJ's named people/topics as positive examples of an underlying taste manifold: market shapers, original framework builders, AI/platform thinkers, elite allocators/operators, and unusually high-leverage intellectuals. Search podcast indexes/web for both watchlist people and *similar* people/topics that fit the same pattern.

Keep the guest/watchlist file as seed examples and calibration anchors, not a closed list. A person like Naval Ravikant should be discovered because he is semantically adjacent to DJ's guidance even if not explicitly named. Do not let a guest name in unrelated footer/link text dominate ranking.

## Default Workflow

1. **Load current configuration and prior outputs.**
   - Inspect source lists, watchlists, skip rules, previous digest outputs, and the episode database when present.
   - Do not assume a cron job exists or is approved; check first.

2. **Resolve RSS feeds.**
   - Use Apple/iTunes search and manual feed URLs.
   - Record unresolved feeds explicitly rather than silently dropping them.
   - Patch obvious wrong/broken feed entries as part of calibration.

3. **Collect recent episodes from known feeds.**
   - Pull a configurable lookback window, usually 1 day for daily digest and 7 days for weekly/prototype runs.
   - Store title, show, description, publication time, URL/audio URL, and source ring.

3a. **Run semantic global discovery.**
   - Required for production daily briefings. Do not treat the known RSS feed list as "the podcast world."
   - Use DJ's named people/topics as examples of a taste manifold, not a closed list.
   - Generate adjacent people/topics/queries, search podcast indexes/web, parse candidate feeds, and insert semantically relevant episodes as `ring3_semantic_discovery`.
   - Current script: `/opt/data/scripts/podcast_semantic_discovery.py --days 1`.
   - The daily footer should separately count known channels scanned and semantic discovery queries/feeds/candidates.

4. **Metadata-rank broadly.**
   - Score by guest/watchlist hits, show quality, title/description concepts, recency, and skip penalties.
   - Treat metadata ranking as a first pass only. It is allowed to be crude; the final digest should not be.

5. **Cluster duplicates.**
   - Collapse the same interview appearing across multiple shows or feed variants.
   - Recommend the best version first, and list alternates only when useful.

6. **Extract content for finalists.**
   - For top candidates, fetch transcripts if available, scrape episode pages, or summarize rich descriptions.
   - Do not transcribe every episode by default; transcribe only finalists to control cost/time.

7. **Curate manually/with LLM judgment.**
   - Re-rank finalists using DJ's relevance test.
   - Promote major CEO/operator/allocator conversations even when metadata keyword score is modest.
   - Downgrade keyword-heavy generic AI/panel/news episodes.

8. **Write the digest.**
   - Use clear tiers: `Must listen`, `Digest only`, `Skim`, `Skip`.
   - For each surfaced item include: why DJ should care, best link/version, likely payoff, and whether to listen or just read the digest.
   - Include a short "what the system deliberately excluded" section when useful to build trust.
   - For prototype/calibration runs, **do not lead only with polished recommendations**. Lead with the funnel: configured sources, resolved feeds, shows with recent episodes, total episodes scored, score distribution, and how many surfaced. DJ needs to judge coverage before judging taste.

8a. **Open-model scoring passes when requested.**
   - If DJ asks to test the live filter on open-source/open-weight models, use OpenRouter/Qwen (or another configured OSS endpoint) for the ranking/summarization layer rather than Codex/Anthropic.
   - Keep Hermes orchestration separate from the filter model: the script can call OpenRouter directly while the agent coordinates the run.
   - For broad daily calibration, use a compact per-episode schema: `{score, tier, reason, confidence}` where tier is `skip | scan | digest | listen` and reason is one short sentence.
   - Run a smoke test first, report token usage/cost, and keep output verbosity low.
   - Prefer the shared helper in `/opt/data/scripts/openrouter_spend.py` (`openrouter_post_json(...)` + `record_openrouter_usage(...)`) instead of hand-rolled `requests.post(...)` calls.
   - If the workflow uses raw HTTP calls, record each OpenRouter response into the Hermes spend ledger and backfill historical artifacts once so the report is complete.

8b. **Daily 24-hour digest runs.**
   - When DJ asks for "today" or a daily run, use a strict last-24-hours `published` window unless he says calendar day.
   - Report the funnel before recommendations: feeds monitored, episodes collected/updated, episodes in the 24h window, episodes scored, and model cost.
   - Generate Qwen episode scores first, then apply DJ's editorial calibration; do not ship raw model ranking as the digest.
   - Avoid placeholder links. If the RSS item has no URL, omit the link rather than inventing one.
   - See `references/daily-digest-calibration.md` and `scripts/qwen_daily_digest.py`.

9. **Ask for calibration before automation.**
   - First runs should be prototypes.
   - Before asking for qualitative feedback on recommendations, produce a source-universe review artifact that DJ can mark up show-by-show.
   - The review artifact should list every resolved source, not just winners: show name, subject/recent episode, guest if known, include/exclude recommendation, reason, confidence level, and links/feed.
   - Ask DJ what was useful/noisy and update scoring/watchlists/skip rules before recurring delivery.
   - Do not enable daily/weekly recurring jobs without explicit approval.
## Weekly audio

- Select the week's 3–5 highest-signal clusters.
- Before scripting, enrich finalists with episode DB lookup + episode page text, and prefer transcript-like grounding when available.
- The weekly script must be **episode-first, not theme-first**:
  - open by naming the actual conversations/guests and their theses;
  - start each main block with show name, episode title, guest, publication/window status, thesis, and why DJ should care;
  - only synthesize cross-episode themes after grounding the listener in the specific episodes.
- Extract the *interesting arguments*, not just the topic label:
  - main claim;
  - supporting evidence;
  - counterargument / unresolved question;
  - why DJ should care;
  - the tradeoff or stake that makes the discussion worth hearing.
- Write a conversational two-host script that guides DJ through named conversations rather than reciting rankings or debating an abstract essay topic.
- Host dynamic: one host is the expert/reviewer who listened/read deeply; the other is the interlocutor whose job is to ask clarifying questions, draw out implications, challenge assumptions, and add useful background/context. Avoid two people taking turns reading the same formulaic summary template.
- If the first draft feels too short or too summarized, expand the editorial analysis instead of compressing harder.
- Report how many finalists were transcript-grounded so coverage is visible, and keep a source-notes artifact beside the script.
- If including a strong calibration holdover outside the strict week/last-7-days window, label it explicitly as a holdover rather than implying it was in-window.
- Then invoke the audio production workflow in this skill to generate the audio file. Speaker labels are script directions, not spoken words.
- See `references/transcript-grounded-weekly-audio.md` for the working recipe and pitfalls.
- See `references/weekly-editorial-calibration.md` for the current lesson on argument-first synthesis, not recap-first compression.
- See `references/weekly-episode-first-digest.md` for DJ's correction that weekly audio must name shows/guests/theses and avoid abstract theme-essay structure.
- See `references/weekly-audio-quality-calibration.md` for the latest host-dynamic and voice calibration: expert/interlocutor format, Kokoro `af_heart` approved for Maya, Piper/Edge judged too robotic.
- See `references/local-tts-backends.md` for local backend notes; update with user calibration before treating any local voice as production-ready.
- Current audio-only finalist path: `/opt/data/venvs/podcast-stt` contains `faster-whisper`/`ctranslate2`; `/opt/data/scripts/podcast_weekly_audio.py` downloads finalist audio, transcribes with `PODCAST_WEEKLY_STT_MODEL` (default `base`), stores transcripts under `/opt/data/podcast_digest/transcripts/`, extracts per-chunk evidence notes with OpenRouter/Qwen, and feeds those notes/excerpts into the weekly script. Leave `PODCAST_WEEKLY_STT_MAX_SECONDS=0` for full production transcription; use a small positive value only for smoke tests.
- Voice calibration update: if Piper sounds robotic, prefer Edge neural voices or a premium cloud TTS. Content structure and host dynamic matter first; but do not assume Piper is better just because it is local. See `references/audio-transcribed-weekly-finalists.md` for the verification gates and pitfalls.

## Audio production workflow

Use this path when the user wants to turn a script, outline, article, or weekly digest outline into a podcast-style audio file.

1. **Prepare a clean production script.**
   - Preserve dialogue structure first; do not flatten MAYA/SAM into one narration blob.
   - Strip markdown bold and speaker labels from spoken TTS text; keep them only for voice assignment.
   - Remove or convert bracketed cues like `[BEAT]`, `[laughs]`, and `[INTRO MUSIC]` into actual pauses or music beds.
   - If the script is dialogue, preserve it as structured segments so each speaker can be synthesized independently.

2. **Chunk long scripts before TTS.**
   - Split by paragraph or speaker turn into chunks of roughly 2,000–3,500 characters.
   - Smaller chunks make retries cheap and reduce provider failures.

3. **Generate TTS.**
   - Prefer premium or highest-quality configured TTS first.
- Use distinct, stable voices for recurring speakers; a slight rate/pitch split helps avoid the "single narrator" effect.
- If the voices still sound mechanical, fix voice identity and dialogue structure first; do not try to polish a bad pairing with more TTS tweaking.
- Keep successful chunks and retry only the failed chunk if one segment errors.
   - For local cost-effective production, prefer **Piper** over `edge-tts` when the goal is better-sounding voices without cloud spend.
   - Use `edge-tts` only as a fallback when local synthesis is unavailable or unacceptably slow.


4. **Normalize the spoken script before synthesis.**
   - Do not rely on raw markdown labels; a script can arrive as `**MAYA:**`, `MAYA:`, or with blank spacer lines after each label.
   - Strip emphasis markers and other inline markup before TTS.
   - If speaker labels appear in the spoken text, regenerate the production pass so the labels are directions only.

5. **Assemble with ffmpeg.**
   - Normalize all chunks to the same sample rate and channel count before concatenation.
   - Add short silence between chunks and place music beds where the script asks for them.
   - Default to MP3 for broad support; use OGG/Opus when a voice-note style delivery is preferred.

6. **Verify before delivery.**
   - Run `ffprobe` on the final file to confirm codec, duration, channels, and sample rate.
   - Ensure all intended segments are present.

7. **Deliver.**
   - On Telegram, include `MEDIA:/absolute/path/to/file` in the final response.
   - Note briefly what was produced and whether it is a polished production or a fallback rendering.


## Output Shape

A daily text digest is a production briefing, not a calibration report. It should contain every episode that qualifies as interesting after filtering, while hiding calibration/debug details unless explicitly requested.

Use this iPhone-friendly plain-text structure:

```text
Podcast Intelligence Briefing — Last 24 Hours

Top line
- 2–4 bullets synthesizing the most important ideas/themes from today's podcast universe.

Must listen / weekly candidates
- Highest-scoring episodes likely to feed the weekly podcast-of-podcasts.
- Include: show, episode, guest if known, one-line thesis, why DJ should care, link.

- Transcript summaries
- Subset of interesting episodes that were important enough to read via transcripts.
- Include the main idea, key supporting points, and action/framework/mental-model takeaway.
- Prefer the episode's *interesting argument* over a compressed recap: what was claimed, what was contested, and what changed in the listener's understanding.

Lightweight summaries
- Interesting episodes where metadata/show notes were enough.
- Include concise summary and why it made the cut.

Worth noting / monitor
- Weak but nonzero signal, especially new themes or people to watch.

Bottom line counts
- Channels viewed: N
- Podcast episodes released: N
- Filtered out: N
- Flagged for lightweight summary: N
- Read via transcript: N
- Must listen / weekly candidates: N
```

Rules:
- Anything that qualifies as interesting should make it into the briefing.
- A subset of interesting/high-score episodes should be read via transcripts and summarized at idea level.
- A smaller subset should be marked as `Must listen / weekly candidate` for the weekly podcast-of-podcasts.
- Counts belong at the bottom as numbers only; do not make the briefing feel like a calibration exercise.
- Do not include calibration notes or model failure analysis in the production briefing unless DJ asks.
- Avoid generic summaries. Be opinionated: "listen to this," "digest only," "skip," "this changes X," "portfolio/operator implication is Y."

## Ranking Pitfalls

- **Opaque calibration**: do not ask DJ to calibrate from a cherry-picked recommendation list alone. He needs the denominator: how many feeds/shows/episodes were examined, what was excluded, and a per-source review list he can edit. Missing this makes the digest feel ungrounded even if the picks are reasonable.
- **AI keyword over-weighting**: many mediocre episodes say "AI" often. Boost only when tied to credible operators, investors, or concrete company implications.
- **Footer/link spam**: guest watchlist names can appear in unrelated show notes, newsletters, cross-promos, or previous episode links. Score only when the name appears in title, guest field, primary description, or transcript context.
- **OpenRouter/Qwen JSON quirks**: if `response_format: {type: json_object}` produces strange thinking/garbled output, remove JSON mode and add `/no_think` plus "Return only JSON". Prefer a smoke test before full scoring.
- **Railway redeploy env visibility**: after DJ adds `OPENROUTER_API_KEY`, terminal subprocesses may not see it even though the gateway does. Check `/proc/1/environ` without printing secrets before declaring the key missing.
- **Direct OpenRouter scripts bypass Hermes spend**: podcast scoring/rendering scripts can call OpenRouter directly and report usage from the API response. Hermes `spend.db` will miss those tokens unless the script emits its own accounting.
- **Dict usage can zero out spend**: if a helper passes `data.get('usage', {})` straight into `normalize_usage()`, convert it to an attribute-style object first or the canonical token counts can collapse to zero.
- **Under-ranking CEOs/operators**: a CEO interview with modest metadata can be more valuable than a keyword-rich panel.
- **Duplicate interview clusters**: same event/interview may appear in multiple feeds. Collapse before presenting.
- **Panel/news formats**: high topicality but often low durable insight. Penalize unless the guests are exceptional or the conversation reveals a reusable framework.
- **Subscription bias**: Ring 1 should calibrate taste, not limit discovery.

## Operational Safety

- Recurring jobs, monitors, and Telegram delivery require explicit approval.
- Keep monitor outputs silent on OK/actionable on alert if health checks are added.
- Do not send emails or external notifications as part of this workflow.
- Use persistent `/opt/data` locations in DJ's production Hermes/Railway environment for durable state; avoid relying on `/tmp` for long-lived assets.
- When reporting spend for podcast work, separate Hermes-session spend from direct OpenRouter script spend instead of assuming `spend.db` is complete.
- For DJ's Telegram Hermes group, production podcast digest outputs belong in **Briefings** (`telegram:-1003956828149:4` as of the current Chief setup). Pipeline failures/health alerts belong in **Alerts** (`telegram:-1003956828149:5`). Experiments/test runs should go to a coding/sandbox topic or stay local until DJ asks to see them.
- Daily podcast delivery wrappers should be bounded: if collection/discovery is slow, time-box those stages, keep semantic discovery optional or separate, and prefer a partial valid digest over a cron timeout. See `references/podcast-digest-cron-fix.md`.

### One-time preview run pattern

When DJ asks to see the podcast digest “today” at a specific time:
1. Confirm current local time with `date` and convert requested ET time to UTC.
2. Create or use a script-only wrapper that prints the final digest on success and an actionable failure message on failure.
3. Run the workflow: collect known feeds → semantic discovery → Qwen scoring → daily digest render.
4. Schedule a one-shot cron job (`repeat=1`) with `deliver=telegram:-1003956828149:4` unless DJ gives another destination.
5. Verify with cron list; describe the schedule in plain English, not raw cron.

## Commands and File Conventions

If using the existing DJ prototype implementation, likely paths are:

```bash
python3 /opt/data/scripts/podcast_resolve_collect_rank.py resolve
python3 /opt/data/scripts/podcast_resolve_collect_rank.py collect --days 7
python3 /opt/data/scripts/podcast_resolve_collect_rank.py digest --days 7
```

Common durable files:

- `/opt/data/podcast_digest/feeds.yaml` — source universe
- `/opt/data/podcast_digest/resolved_feeds.yaml` — resolved RSS feeds
- `/opt/data/podcast_digest/guest_watchlist.yaml` — high-signal people
- `/opt/data/podcast_digest/skip_rules.yaml` — scoring/skip rubric
- `/opt/data/podcast_digest/episodes.sqlite` — episode store
- `/opt/data/podcast_digest/outputs/` — digest artifacts

These paths are conventions, not universal facts. Verify them before editing.

## References

- `references/prototype-radar-notes.md` — condensed notes from the first DJ prototype run, including source model, scoring lessons, and calibration findings.
- `references/openrouter-qwen-episode-scoring.md` — OpenRouter/Qwen setup notes, Railway env visibility quirk, compact scoring schema, and observed cost from the 100-episode calibration pass.
- `references/openrouter-spend-attribution.md` — how to attribute OpenRouter usage from the podcast scripts into Hermes spend reporting, including backfill keys and stage names, plus the dict-usage normalization pitfall.
- `references/openrouter-accounting-bug-and-backfill.md` — the dict-normalization pitfall, symptom, and one-time ledger backfill recipe.
- `references/openrouter-usage-object-quirk.md` — the dict-vs-object usage bug that can zero out podcast spend, plus the backfill/verification pattern.
- `references/openrouter-direct-accounting.md` — legacy/raw HTTP accounting notes for podcast scripts, plus the reason to prefer the shared helper for new code.
- `references/openrouter-shared-helper.md` — shared helper API, rollout pattern, and verification checklist for new podcast scripts.
- `references/daily-digest-calibration.md` — 24h daily digest workflow, funnel reporting requirements, DJ editorial calibration, and first-run lessons.
- `references/last48h-run-notes.md` — June 2026 ad hoc 48h run notes, interpreter pitfall, and successful digest shape.
- `references/multi-speaker-dialogue.md` — structured dialogue-segment notes for producing multi-voice podcast audio.
- `references/weekly-audio-pipeline.md` — working recipe for DJ's weekly original audio briefing, including chunking, TTS, ffmpeg re-encode, and Telegram delivery.
- `references/transcript-grounded-weekly-audio.md` — transcript/page-grounded finalist workflow for deeper weekly audio.
- `references/weekly-editorial-calibration.md` — current lesson on argument-first synthesis, not recap-first compression.
- `references/weekly-episode-first-digest.md` — DJ's correction that weekly audio must be structured around named episodes/shows/guests/theses before cross-episode synthesis.
- `references/local-tts-backends.md` — local TTS backend comparison and the practical Piper default.
- `references/podcast-digest-cron-fix.md` — bounded cron wrapper and failure-mode notes for daily delivery.
- `scripts/qwen_daily_digest.py` — starter script that turns Qwen episode scores into a calibrated daily markdown digest.
- `scripts/qwen_episode_score.py` — reusable starter script for compact OpenRouter/Qwen episode-level scoring against the prototype SQLite episode store.

## Verification Checklist

- [ ] Feed resolution errors are visible and not silently ignored.
- [ ] Episode collection produced expected row counts or a clear failure.
- [ ] Ranking does not rely only on keyword density.
- [ ] Duplicates/clusters are collapsed.
- [ ] Finalist content was inspected beyond metadata where possible.
- [ ] Digest uses DJ-specific tiers and recommendations.
- [ ] Calibration notes are captured before automation.
- [ ] No recurring delivery or cron job was enabled without explicit approval.
