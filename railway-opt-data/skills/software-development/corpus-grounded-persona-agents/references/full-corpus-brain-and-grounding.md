# Full-Corpus Brain Extraction + Claim-Level Grounding

Reusable pattern from the Ben Bot/Horowitz-agent repair where a narrow manual RAG brain was expanded into corpus-wide reasoning and paired with fail-closed grounding.

## Full-corpus brain extraction

Use this when the user asks how the agent knows it is using the whole corpus or complains that answers are too generic/extractive.

1. Start from canonical chunks, not source files: e.g. `chunks/chunks.jsonl` with `source_id`, title/date metadata, text, controlled topics, and summaries.
2. Build deterministic coverage accounting before generation:
   - total chunks scanned
   - unique sources represented
   - controlled topic tags observed
   - chunks per topic/source
3. Group chunks by controlled topic tags and high-signal keywords.
4. For each group, generate or deterministically synthesize concept records with:
   - `id`, `label`, `summary`
   - `keywords`
   - `claims` grounded to source IDs
   - `decision_rules` for applying the worldview to new questions
   - `source_ids` and example chunk IDs
5. Emit both machine data and human audit output, e.g. `persona/corpus_brain.json` plus `persona/corpus_brain_coverage.md`.
6. Tests should assert that major topic groups are represented and that concept records are anchored to real source/chunk IDs.

Avoid hand-maintaining only a few demo concepts. A brain that does not report corpus coverage will regress into one-question hard-coding.

## Claim-level grounding checker

Answer-level citation checks are insufficient. They miss citation laundering: one valid cited sentence followed by unsupported advice in the same paragraph or bullet.

Recommended validator:

1. Parse inline citations and validate them against the retrieved/allowed source set using the same rules as runtime source-card filtering.
2. Split the answer into claim units:
   - bullets/list items
   - sentences within paragraphs
   - short imperative units if they contain high-stakes action verbs
3. Ignore non-substantive units such as greetings, connective phrases, and very short setup clauses.
4. A unit is substantive if it is long enough to make a claim (project used ~55 chars) or contains action/decision verbs such as `hire`, `fire`, `sell`, `buy`, `acquire`, `fundraise`, `lay off`, `promote`, `replace`, `shut down`.
5. Require each substantive unit to contain at least one citation that resolves to the retrieved source set.
6. Catch adversarial cases:
   - no citations anywhere
   - unmatched citation title/year
   - valid citation followed by uncited advice in the same paragraph
   - bullet with cited setup plus uncited recommendation
   - mixed valid and invalid citations
   - weak one-token citations like `[CEO, 2011]`

## Runtime behavior

- First generation: normal grounded composer prompt.
- If grounding fails: send the exact checker errors back as feedback and allow one regeneration.
- If retry fails: return a grounded-error/abstention response. Do not return deterministic snippet glue or generic persona advice.

## Verification

- Unit tests for parser behavior and laundering cases.
- Composer tests for first-pass success, retry success, and fail-closed retry failure.
- Product interaction eval with multi-turn practical advice, out-of-corpus traps, and source-card/citation alignment.
- Before claiming done, run the app in production or against the deployed endpoint; endpoint health alone is not enough.
