# Full-site author coverage audit

Use this reference when a public-figure corpus is built from a modern publisher/company site and a known source gap suggests the original discovery method undercounted live canonical pages.

## When to run it

Run after any missed-source complaint or before declaring blog/essay coverage gate-ready when the site has migrated legacy content. Wayback CDX, XML sitemaps, and author archive pagination can each be incomplete. A full-site crawl plus author-metadata verification gives a stronger regression gate.

## Pattern

1. Build the broad candidate URL set from multiple site-native indexes:
   - HTML sitemap pages, not only XML sitemaps.
   - Author archive pages.
   - Relevant category/topic archive pages.
   - Search pages if exposed by the site.
2. Filter out obvious non-content classes before fetching: podcasts, books, category pages, tag pages, image/assets, query-only tracking URLs.
3. Fetch every candidate page and inspect authoritative metadata:
   - canonical URL
   - publish/modified date
   - title / OpenGraph title
   - `meta[name=author]`, JSON-LD `author`, byline links, `twitter:data*`
   - speaker/guest fields for podcast-like pages
4. Classify a page as target-authored only when metadata or byline evidence says the target is the author/speaker. Do not ingest pages that merely mention the person in related links or nav.
5. Normalize titles and canonical URLs, then diff against both `bibliography.jsonl` and `corpus/` frontmatter. Track each candidate as `present`, `missing`, or `excluded` with reason.
6. Ingest verified misses from the live canonical artifact or from a public collection artifact when no standalone URL can be verified.
7. Rebuild all serving layers after corpus repair: bibliography/manifest, corpus, chunks, retrieval index, citation/source metadata, tests, and deployed runtime if applicable.
8. Add a regression test that reruns the audit and fails if any verified target-authored candidate is missing.

## Evidence to report

- Count of candidate links by index source.
- Count of unique non-podcast/non-book URLs checked.
- Count of verified target-authored candidates.
- Count missing before repair and after repair.
- List of any unresolved verified candidates.
- Validator/test command and result.
- A few live retrieval/API probes proving repaired sources rank and return canonical URLs in citations.

## Example result shape

- HTML sitemap: 1,474 candidate links.
- Author page: 33 candidate links.
- Leadership category: 40 candidate links.
- Company-building category: 25 candidate links.
- Unique non-podcast/non-book URLs checked: 1,482.
- Verified Ben-authored candidates: 83.
- Missing after repair: 0.

## Pitfalls

- XML sitemap absence is not evidence of source absence. Legacy migrated WordPress slugs often live at clean canonical URLs omitted from current XML sitemaps.
- Related-content widgets create false positives; require author/byline metadata.
- A deterministic bibliography validator can pass while discovery is incomplete; discovery audits need an independent expected-candidate set.
- After adding records, retrieval may still fail if chunks or composer/source-card metadata were not rebuilt to propagate canonical URLs.
