# Citation fail-closed patterns for corpus persona agents

Session-derived notes from repairing a Ben Horowitz corpus agent after independent review failures.

## Failure mode

A generated answer can look grounded even when source cards and citations are not actually aligned:

- The LLM returns substantive claims with no inline citations; the app still displays retrieved source cards.
- The LLM returns one valid citation plus one hallucinated citation; filtering drops the unmatched card but leaves unsupported citation text in the answer.
- A fuzzy matcher lets generic one-token citations like `[CEO, 2011]` match titles such as `Peacetime CEO/Wartime CEO`.
- Product eval parsing handles only the first title in `[A, 2010; B, 2023]`, falsely reporting source-card mismatch.

## Runtime fix pattern

Implement citation handling in two layers:

1. `extract_citations(answer)`: collect every bracketed citation and split semicolon-separated groups into independent normalized titles.
2. `unmatched_citations(answer, retrieved_sources)`: validate every extracted title against the explicit retrieved source-title allowlist.

Accept an LLM answer only when:

- at least one citation exists;
- every citation resolves to one or more retrieved source titles;
- the final displayed source list is non-empty and consists only of cited retrieved sources.

Otherwise return a fail-closed response with no source cards, or regenerate with stricter instructions. Do not silently present retrieved sources as support.

## Prompt guardrail

Do not rely only on free-form instructions like “cite retrieved titles.” Add an explicit allowed-citation block to the model prompt:

```text
Allowed citation titles — every inline citation must use one of these exact titles, not people/books mentioned inside excerpts:
- On Micromanagement, 2010
- The Hard Things About Scaling: Executive Hiring, 2023
```

Then enforce the same allowlist in code. This reduces cases where the model cites works or people mentioned inside excerpts (for example books, executives, or concepts) rather than the retrieved corpus source title.

## Matching guardrails

- Strip publisher suffixes like `| Andreessen Horowitz` and years before matching.
- Allow exact matches, normalized substring matches, and strong multi-token overlap.
- Reject citations with fewer than two meaningful tokens; this prevents `[CEO]`, `[Cares]`, and similar generic references from overmatching.
- Prefer overlap denominator `max(len(citation_tokens), len(title_tokens))`, not `min(...)`, so a one/two-token citation cannot fully match a long title by sharing a small subset.

## Test cases to add

- No citation in LLM answer ⇒ fail closed, `sources == []`.
- Citation that matches no retrieved source ⇒ fail closed.
- Mixed valid + invalid citation group ⇒ fail closed.
- Semicolon-separated valid citations ⇒ all relevant source cards kept.
- Generic one-token citation ⇒ no match/fail closed.
- Deterministic/provider-unavailable fallback ⇒ no snippet stitching or persona impersonation.

## Product eval note

Keep product-eval citation parsing consistent with runtime parsing. In particular, split bracketed semicolon citations before comparing source cards, otherwise valid answers like `[On Micromanagement, 2010; The Hard Things About Scaling, 2023]` may be incorrectly marked as showing an uncited second source.
