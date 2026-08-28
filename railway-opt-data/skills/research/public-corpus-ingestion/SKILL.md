---
name: public-corpus-ingestion
description: "Use when building a private/public-source corpus and bibliography from web archives, sitemaps, RSS feeds, podcast/video pages, and seed lists. Emphasizes source verification, legal constraints, cleanup validation, coverage reporting, and gate-ready deliverables."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [corpus, bibliography, web-archives, rss, transcripts, validation]
    related_skills: [youtube-content, blogwatcher, github-repo-management, corpus-grounded-persona-agents]
---

# Public Corpus Ingestion

## Overview

Use this skill for projects that ask for a verified corpus from public sources: author blogs, company sites, RSS feeds, podcasts, YouTube/videos, interviews, and seed-list coverage audits. The key risk is false confidence: search results prove existence, not coverage; a fetched page proves access, not that the cleaned corpus contains the target person's words.

The goal is a gate-ready corpus with raw artifacts, cleaned markdown, machine-readable bibliography, human bibliography, coverage report, blockers, and reproducible validators.

## When to Use

- Building a private RAG/persona corpus from a public figure's writing, talks, podcasts, or interviews.
- Producing `bibliography.jsonl`, `bibliography.md`, `coverage_report.md`, or seed-list hit/miss audits.
- Enumerating source classes from archives/sitemaps/RSS rather than ad hoc search.
- Cleaning HTML/podcast/video sources into frontmatter-bearing markdown.
- Auditing whether the cleaned corpus is truly source text, not boilerplate, show notes, related links, or third-party summaries.

Don't use for: one-off article summaries, academic paper search only, or already-curated datasets that do not require acquisition/cleaning.

## Core Workflow

0. **Resolve user corrections before finalizing.** If the user says coverage is not good enough, do not defend the gate packet. Re-open Phase A, inspect the missed source classes, repair the corpus, rerun validators/audits, commit a replacement gate packet, and keep the human gate stopped.
1. **Create the repo scaffold first.** Include `raw/`, `corpus/`, `bibliography/`, `scripts/`, `decisions/`, `BLOCKERS.md`, and `RUNLOG.md`. Commit a `scaffold` before acquisition so gate diffs are understandable.
   - For DJ projects, GitHub or DJ’s personal Google Drive is the durable destination. Treat Railway/VM `/opt/...` paths as temporary working cache, not as where artifacts “live.”
   - If raw artifacts are bulky, push them to GitHub/Drive for provenance, then keep the live VM checkout lightweight with blobless clone/sparse checkout excluding `raw/` unless actively ingesting.
2. **Write the user's runbook/seed files verbatim if supplied.** Do this before discovery. Do not “clean up” tables, punctuation, or odd line breaks in documents the user asked to preserve exactly.
3. **Enumerate by source class.** For enumerable classes, use the archive itself:
   - Wayback CDX for old domains.
   - XML sitemaps / sitemap indexes for modern sites.
   - RSS feeds for podcasts/shows.
   - `yt-dlp --flat-playlist` for YouTube channels/playlists.
   - Search/directories only for best-effort classes that lack a canonical archive.
4. **Record candidate counts before fetching.** Coverage reports should say method, raw count, deduped count, ingested count, and whether the class is “enumerated by <method>” or “best-effort.” Never call a class complete.
5. **Fetch raw artifacts into `raw/`.** Store exact source URL, fetch timestamp if required, and SHA256 in the bibliography record.
6. **Clean into `corpus/{id}.md`.** Use YAML frontmatter matching the bibliography schema. Keep source words; do not paraphrase.
7. **Generate both bibliography forms.** `bibliography.jsonl` is one JSON object per source. `bibliography.md` is grouped by medium/year/status for human review.
8. **Run deterministic validators.** At minimum: every ingested bibliography record has a corpus file; every corpus file has valid frontmatter; word counts are positive; ids match; status values are allowed.
9. **Run an independent quality audit.** Sample across medium/source classes. The reviewer should check boilerplate, dates, speaker labels, and whether the text is truly the target person's words.
10. **Repair from the raw artifacts, not from guesses.** If cleanup dropped the real article body or retained comments/page chrome, re-extract from the saved raw HTML and rerun validators/audits. A deterministic validator can pass while the corpus is still bad; do not treat validator success as a substitute for audit verdicts.
11. **Do not finalize with known audit failures.** If the independent audit reports missing book sections, trailing legal/chrome, duplicated epigraphs, bad dates, or unusable transcripts, fix those issues and run at least a targeted re-audit before committing the gate packet.
12. **Produce the gate packet and stop at the gate.** Include bibliography, coverage report, sample pack, blockers, run log, spend/transcription time, commit, push, and do not proceed to later phases without explicit approval.

## Enumeration Patterns

### Public books / PDFs

Do not assume books are unavailable just because they are commercially published. First check the user's supplied URLs and search for public PDFs/pages; if the user explicitly says a PDF is public, fetch it into `raw/books/`, hash it, extract with PyMuPDF, split into chapter-level corpus files, and record the public source URL. If no public/user-supplied copy is available, then mark `not_available`.

Use `uv run --with pymupdf --python /opt/hermes/.venv/bin/python ...` when the active Python lacks pip but `uv` exists. Split books from actual chapter headings in extracted text, not from the table of contents; watch for line-wrapped headings like `Introduction: What You Do Is\nWho You Are`.

### Wayback CDX for archived blogs

```bash
curl -s 'https://web.archive.org/cdx/search/cdx?url=example.com/*&output=json&collapse=urlkey&fl=original,statuscode,mimetype,timestamp&filter=statuscode:200' > raw/cdx.json
```

Filter dated post URLs, remove `wp-content`, feeds, trackbacks, comments, attachments, and duplicate `www`/`:80` variants. If the runbook has a sanity floor, compare the deduped post count to it before claiming acceptance.

### Sitemaps for modern sites

1. Fetch `https://domain/sitemap_index.xml`.
2. Pull relevant child sitemaps: `post-sitemap*.xml`, `podcast-sitemap*.xml`, `page-sitemap*.xml`, `book-sitemap*.xml`.
3. For migrated author blogs, map archived slugs to likely canonical URLs on the modern site (for example `oldblog.com/YYYY/MM/DD/slug/` → `https://modernsite.com/slug/`) and fetch those canonical copies before giving up. Many old blog posts are findable this way even when author archive pagination/search is poor.
4. Do not trust Wayback + sitemap as the only archive for migrated legacy blogs. Legacy pages can be live and author-tagged while absent from both Wayback CDX and current sitemaps. Look for secondary canonical indexes: ebook/PDF collections, "from blog to ebook" pages, category/topic archives, Medium mirrors, publisher collections, and prominent article cross-links.
5. If any known/random canonical post is missing, escalate from spot repair to a broad full-site author audit: crawl HTML sitemap pages, author pages, and relevant category archives; fetch candidate pages; verify target authorship from metadata/bylines; then diff against bibliography and corpus. See `references/full-site-author-coverage-audit.md`.
6. Fetch pages and inspect metadata (`meta[name=author]`, JSON-LD, `twitter:data2`, title, canonical URL), not just body text. Body text often includes related links that mention the target person.
7. Treat pages that only mention the target in recommendations/navigation as `excluded`, not ingested.

### YouTube playlists/channels

Use YouTube as a first-class podcast/video archive when shows publish there. Enumerate with:

```bash
python -m yt_dlp --flat-playlist --dump-single-json 'https://www.youtube.com/playlist?list=PLAYLIST_ID' > raw/youtube/playlist.json
```

Then fetch transcripts with `youtube-transcript-api` or `yt-dlp --write-auto-subs --skip-download`. Record transcript misses separately and queue them for local transcription rather than marking the whole class failed. Flat playlist metadata may omit upload dates; for ingested YouTube records, resolve each video date with full `yt-dlp --skip-download --print '%(upload_date)s' URL` or mark the date as approximate/pending in notes. Auto-caption transcripts are acceptable only if notes say they are undiarized/auto-captioned; do not claim speaker-clean diarization.

### RSS and transcript search for podcasts

RSS enumeration can prove an episode exists and expose show notes, but show notes are not a transcript. Only mark as ingested corpus when:

- A public transcript exists in the page/feed or a transcript host/page that resolves to the same episode, or
- You locally transcribed the audio, validated word counts, and applied speaker cleanup.

Otherwise keep the metadata as `not_available` / `needs_transcription` per the runbook and log the blocker.

When the user narrows podcast scope by theme (for example culture, leadership, management), run a focused thematic pass after broad enumeration:

1. Search targeted combinations of person + theme + show + `transcript` across multiple public transcript hosts, show blogs, GitHub transcript repos, and publisher pages.
2. Fetch raw HTML/markdown into `raw/`; preserve the source URL and hash.
3. Ingest only substantial transcript text. Treat thin episode summaries, recaps, or AI digests as `not_available`/excluded unless the runbook permits summaries.
4. Keep duplicate transcript sources temporarily when comparing transcript quality, but mark in the coverage report that duplicates may be deduped later before chunking.
5. Recompute bibliography/coverage/sample-pack counts and rerun validators immediately after the thematic pass.

## Cleaning Rules

- Strip comments/replies, related posts, newsletter promos, social share widgets, legal disclaimers, navigation, sidebars, and power-user menus.
- Preserve source epigraphs, quotes, headings, and author notes that are part of the article.
- De-duplicate repeated epigraphs or paragraphs created by archive/readability extraction.
- For third-party interviews/profiles, either keep only the target person's quoted speech plus minimal context, or mark as mixed/limited in notes. Do not let a journalist's full article become “the target's words.”
- For transcripts, require speaker labels. If the source labels speakers as `Ben:`/`Host:` etc., keep labels. If labels are absent and diarization is not done, do not pretend the transcript is speaker-clean.
- Recompute word counts after every cleanup pass.

## Validators to Include

Minimum validator checks:

```python
# Pseudocode
records = load_jsonl('bibliography/bibliography.jsonl')
for corpus_file in glob('corpus/*.md'):
    frontmatter = parse_yaml_frontmatter(corpus_file)
    assert frontmatter['id'] in records
    assert records[frontmatter['id']]['status'] == 'ingested'
for record in records:
    if record['status'] == 'ingested':
        assert Path('corpus', record['id'] + '.md').exists()
        assert record['word_count'] > 0
```

Additional useful checks:

- No corpus file contains obvious boilerplate markers: `Power User Menu`, `Related`, `Subscribe`, `Privacy Policy`, `## <N> Replies`, `Link copied`.
- Podcast corpus files contain a transcript heading and speaker labels.
- Seed-list found items resolve to an ingested record with a raw artifact hash.
- Raw artifacts exist for every ingested public source.

## Coverage Report Shape

Use direct bullets, not tables when reporting via Telegram:

- Seed coverage: `found / total`; paywalled; not_found; not_available; excluded.
- Per class: method, raw count, deduped count, ingested count, enumerated/best-effort.
- Per medium: records and ingested counts.
- Per year: ingested counts.
- Total ingested sources and total words.
- Seed-list audit: one line per seed with status and reason.
- Secondary-index audits: for every independent index used (PDF/ebook TOC, author collection, mirror archive), report total items, found-before-repair, missing-before-repair, found-after-repair, and unresolved items. A random missed canonical source invalidates the coverage claim until at least one independent index is diffed against the corpus.
- What was excluded and why.
- Acceptance check evidence: validator command, exit code, sample IDs audited.
- Blockers and spend/transcription wall-clock.

Support files:
- `references/horowitz-phase-a-lessons.md` captures detailed lessons from a Phase A public-figure corpus run.
- `references/legacy-blog-secondary-index-audit.md` gives a reusable pattern for auditing migrated legacy blogs against independent PDF/ebook/category indexes when Wayback+sitemap coverage misses live canonical posts.
- `references/full-site-author-coverage-audit.md` gives a reusable pattern for crawling broad site-native indexes, verifying author metadata, diffing against the corpus, and adding regression gates after missed-source complaints.

## Transition to Persona/Agent Runtime

After a corpus gate is approved, do not assume RAG alone will create an intelligent persona. For private figure/advisor bots, load `corpus-grounded-persona-agents` before designing Phase B+ runtime, persona, retrieval, or evaluation. The next layer should extract corpus-wide principles/decision rules, preserve multi-turn context, validate citation/source alignment, and run product-grade conversation probes.

## Common Pitfalls

1. **Assuming books are unavailable.** If the user supplies a public PDF URL or states public PDFs exist, ingest those public PDFs and split them by chapter. Only use “owned copies only/not_available” when no public/user-supplied copy is available or when the runbook explicitly forbids public copies.
2. **Counting show notes as transcripts.** A podcast page with a description is not source speech. Mark it not_available/needs_transcription unless a public transcript or local transcript exists.
3. **Ignoring YouTube as the canonical podcast archive.** Many podcast episodes are published as YouTube playlist videos with accessible captions. Enumerate the playlist/channel and fetch captions before declaring podcasts unavailable.
4. **False positives from related-content widgets.** Modern sites often include the target person's name in recommended content. Verify metadata/authorship/speaker lists before ingesting.
5. **Wayback/sitemap blind spots for migrated legacy posts.** A legacy post may be absent from Wayback CDX for its original dated URL and absent from modern XML sitemaps while still live at a canonical migrated URL. If a random known post is missing, audit against independent collections/TOCs before calling it isolated.
6. **Exact-title audits need careful normalization.** Normalize curly/straight apostrophes, `can't`/`cant`, subtitles, wrapped PDF TOC lines, and punctuation. Avoid fuzzy body-text matches for short titles like “Andy” or “Bill”; require exact title/URL or a strong token match.
7. **Readability extraction can drop the body.** If a cleaned file is suspiciously short or mostly navigation, inspect `raw/` and re-extract with source-specific selectors like `div.entry-content`.
8. **Comments are not corpus.** Old WordPress/Wayback pages commonly include `## 22 Replies` and commenter text. Strip all comments/replies/trackbacks.
9. **Third-party profiles are mixed source.** Unless the runbook explicitly allows context, extract only quoted target speech and label notes accordingly.
10. **Huge raw directories make noisy commits.** Use `git status --short`, `git commit --quiet` when possible, and verify final status/log rather than relying on massive commit output.
11. **Do not fabricate completeness.** Say “enumerated via Wayback CDX, count=N,” not “complete archive.”
12. **Gate means stop.** If the runbook says Phase A only, do not start chunking, embedding, persona writing, deployment, or eval.

## Verification Checklist

- [ ] Runbook and seed list written exactly when supplied.
- [ ] Scaffold committed before acquisition.
- [ ] Source classes enumerated by named methods with raw/deduped/ingested counts.
- [ ] Books or paid sources only ingested if user-provided owned files exist.
- [ ] Corpus files have valid frontmatter and matching bibliography records.
- [ ] Raw artifacts and SHA256 hashes exist for ingested public sources.
- [ ] Podcast/video files are transcript-backed or marked unavailable/blocked.
- [ ] Independent quality audit sample and verdicts are in `RUNLOG.md`.
- [ ] `coverage_report.md`, `sample_pack.md`, `BLOCKERS.md`, `RUNLOG.md`, and ADR are current.
- [ ] Final commit and push completed.
- [ ] Final message is short, includes repo link, seed coverage, counts, blockers, spend, and link to coverage report.
