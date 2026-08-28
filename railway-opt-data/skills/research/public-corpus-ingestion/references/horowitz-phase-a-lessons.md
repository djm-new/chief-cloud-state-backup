# Horowitz Phase A Lessons

Session-specific lessons from a Phase A corpus/bibliography run for a private Ben Horowitz agent.

## User correction that changed the workflow

DJ rejected a first Gate 1 packet because it under-counted available material:

- The books had public PDFs; do not default to `not_available` just because books are commercial.
- Former `bhorowitz.com` blog posts were generally findable as canonical `a16z.com/<slug>/` pages.
- Ben & Marc/a16z podcast material was on YouTube, with many accessible transcripts/captions.

The fix was to redo Phase A rather than patch the report cosmetically: fetch/extract PDFs, map archived blog slugs to a16z canonical URLs, enumerate the YouTube playlist, ingest captions, rerun validators, then push a replacement Gate 1 commit while still stopping at Gate 1.

## What worked

- Wayback CDX enumeration under `bhorowitz.com/*` with `collapse=urlkey` found a stable dated-post set. Filtering to `/YYYY/MM/DD/slug/` and excluding `wp-content`, feeds, trackbacks, comments, and attachments produced the source candidate list.
- Mapping `bhorowitz.com/YYYY/MM/DD/slug/` to `https://a16z.com/slug/` recovered many canonical blog copies that were cleaner and publicly hosted on a16z.
- Public PDFs were fetched into `raw/books/`, hashed, extracted with PyMuPDF via `uv run --with pymupdf`, and split into chapter-level corpus files. Chapter splitting must use actual body headings, not the table of contents.
- `yt-dlp --flat-playlist --dump-single-json` against the Ben & Marc Show playlist enumerated videos; `youtube-transcript-api` retrieved many transcripts/captions. Full `yt-dlp --skip-download --print '%(upload_date)s' URL` resolved dates absent from flat playlist metadata.
- A focused culture/leadership podcast pass improved the corpus after broad enumeration. Search targeted `Ben Horowitz + culture/leadership/management + transcript` combinations across show pages, transcript hosts, GitHub transcript repos, and publisher pages; then ingest only substantial public transcript text. Useful targets found in this run included Tim Ferriss, Lenny, My First Million, Ritholtz/Masters in Business, a16z “Companies & Culture,” and “What Makes a Great Founder.” Thin recaps/AI digests and blocked transcript pages stayed as `not_available`.
- Modern `a16z.com` exposed a Yoast `sitemap_index.xml` with `post-sitemap*.xml`, `podcast-sitemap*.xml`, `book-sitemap.xml`, and related child sitemaps. This was better than guessing author archive URLs.
- Deterministic validators caught bibliography/corpus mismatches quickly: JSONL record IDs, corpus frontmatter IDs, ingested status, and positive word counts.
- Independent model audit was valuable: it caught WordPress comments, a16z page chrome, podcast show-notes masquerading as corpus, an article whose cleaned markdown had lost the real body, missing book intro sections, bad dates, and obvious caption/entity errors.

## Pitfalls observed

- A naive `"Ben Horowitz" in HTML/text` filter on a16z pages over-ingested hundreds of false positives because related-content widgets mention Ben. Keep only pages where metadata/title/speaker fields identify him as author/speaker/guest.
- Podcast pages with show notes should not be marked as ingested corpus unless a public transcript/caption or local transcription exists. Moving non-transcript podcast pages to `not_available` makes counts more honest.
- YouTube auto-captions are source transcripts but not speaker-clean. Record them as undiarized/auto-captioned; fix obvious entity errors only when clearly mechanical (`Opswear` → `Opsware`, `Mark` → `Marc`) and never paraphrase.
- Readability extraction on old WordPress/Wayback pages can retain `## N Replies` comments or, in some cases, drop the article body. Re-extract from raw HTML using `div.entry-content` or `article` and inspect short files manually.
- A16z current pages often leave trailing author cards, recommendation lists, newsletter prompts, and legal disclaimers after the article body. Cut at markers such as `Expert News by a16z`, `Subscribe to the a16z newsletter`, `This information is provided by`, `The views expressed here`, and related-content headings.
- Third-party profiles such as New Yorker articles may be useful seed hits, but they are not clean first-person source text. Either keep only paragraphs with the target's quotes/context and mark notes as mixed, or exclude.
- Large `raw/html` directories produce enormous `git commit` output. Use quiet flags or redirect output when the exact file list is not useful.

## Gate-reporting shape that matched the runbook

Final message should be short and include: repo link, Gate 1 stop, seed coverage, per-medium ingested counts, blockers, spend/transcription hours, and a link to `bibliography/coverage_report.md`.
