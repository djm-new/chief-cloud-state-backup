# Corpus-Grounded Agent Debugging

Use this when a RAG/persona/corpus agent technically returns answers but the user says it is not thinking, is unrelated, is too extractive, or fails follow-up context.

## Failure pattern

A corpus agent can pass endpoint, retrieval, and citation tests while still failing the product:

- It keyword-matches the latest user text instead of resolving conversational referents.
- It treats retrieved excerpts as the whole brain, so follow-ups that require inference produce awkward refusals or unrelated snippets.
- It imports generic advice and backfills citations, or over-corrects into exact-text extraction.
- It validates `/health`, `/chat`, and “has sources” rather than real interactive quality.

## Debugging sequence

1. Reproduce with the exact multi-turn exchange the user found bad.
   - Send history, not just isolated questions.
   - Record resolved question, matched concepts, retrieved source titles, answer, and UI-visible source list.
2. Identify which layer failed:
   - UI did not send prior turns.
   - Query rewriting did not resolve the referent.
   - Retrieval matched surface words instead of the live concept.
   - Composer refused to infer or stitched snippets.
   - Citations named sources not shown in retrieved/source payload.
3. Add regression tests for the failure class before fixing:
   - A follow-up like “when does it become toxic?” after a micromanagement answer must resolve to the micromanagement concept.
   - Expanded retrieval must include corpus concept terms/citation anchors, not just the literal follow-up words.
   - The answer prompt must include structured concept/decision-rule context.
4. Build or update a corpus-brain layer when raw retrieval is insufficient:
   - concepts/principles
   - explicit corpus claims
   - corpus-derived decision rules
   - adjacent concepts
   - citation anchors
5. Runtime should answer from: conversation history + resolved question + matched corpus-brain concepts + retrieved excerpts.
6. Verify with live product interaction, not only unit tests.

## Correct answer contract

The target is not extractive RAG and not generic LLM advice. It is corpus-conditioned inference:

- All thinking comes from the corpus-derived worldview.
- The model may infer from corpus concepts and decision rules.
- It must distinguish direct source claims from applications/inferences when useful.
- It must not import generic frameworks that are absent from the corpus.
- Final citations should correspond to retrieved/source-card-visible sources.

## Acceptance checks

- Unit tests cover referent resolution and concept-aware retrieval.
- Interaction eval covers at least one multi-turn failure transcript.
- Live deployed UI/API has been tested with history-carrying follow-ups.
- Product-green is separate from infrastructure-green: endpoints and tests passing are not sufficient if the deliverable is an interactive advisor.
