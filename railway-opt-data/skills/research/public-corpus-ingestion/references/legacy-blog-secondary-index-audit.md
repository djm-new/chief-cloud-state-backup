# Legacy blog secondary-index audit

Use this reference when a public-figure corpus has migrated legacy blog posts and a random known post is missing.

## Why this matters

A missed canonical blog post is evidence that the coverage method is incomplete. In one Ben Horowitz corpus repair, `On Micromanagement` was live at `a16z.com/on-micromanagement/` with `meta author=Ben Horowitz`, but it was absent from:

- Wayback CDX queries for `bhorowitz.com/*micromanagement*`
- Wayback CDX queries for `bhorowitz.com/2010/04/05/*`
- Current a16z XML sitemaps tested during the repair

The independent source that revealed the broader gap was a public a16z PDF collection: `Some More Things`.

## Audit pattern

1. Find secondary indexes beyond Wayback + sitemap:
   - PDF/ebook collections of selected posts
   - “blog to ebook” announcement pages
   - category/topic archives
   - Medium mirrors by the same author
   - prominent cross-links from podcasts/interviews
2. Extract the index/TOC into a deterministic list of expected titles.
3. Diff expected titles against `bibliography.jsonl`/`corpus/` using strict normalized source-title matching.
4. Avoid fuzzy body-text matches for short titles such as `Andy` or `Bill`; they create false positives from mentions inside unrelated files.
5. Verify each missing title by either:
   - fetching a live canonical page with author metadata, or
   - extracting the section from the public index artifact if no standalone URL exists and the artifact itself is a public source.
6. Re-run the audit after ingestion and report before/after counts.

## Title normalization checklist

Normalize:

- curly and straight apostrophes
- `can't` / `cant` / `can t`
- `don't` / `dont` / `don t`
- wrapped PDF TOC lines
- subtitles appended on the canonical site
- possessives such as `Shareholders'` vs `Shareholder’s`

## Evidence to put in the coverage report

- Audit source URL and raw artifact path
- TOC/index item count
- found-before-repair
- missing-before-repair
- found-after-repair
- list of unresolved items, if any
- exact validator commands and test results

## Example result shape

- Independent audit source: `raw/audit/Some-More-Things.pdf` from a16z.
- Before repair: 23 TOC blog posts checked; 8 found in corpus; 15 missing.
- After repair: 23/23 found. Added 15 records as individual corpus files; 14 live canonical pages plus one PDF-only section where no standalone URL verified.
