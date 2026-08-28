# Ben Bot Reasoning Repair — Session Lessons

This reference captures reusable details from a private Ben Horowitz persona-agent repair. Keep it as a pattern, not as a project log.

## Failure observed

The deployed bot had healthy infrastructure but behaved like a snippet-stitcher:

- It retrieved relevant chunks but answered by gluing excerpts instead of advising from Ben's worldview.
- It did not reliably preserve multi-turn context for short follow-ups.
- The visible source list could include retrieved sources the answer did not actually cite.
- A deterministic fallback risked producing low-quality pseudo-persona answers when the LLM composer was unavailable.

## Repair pattern that generalized

1. **Add a structured corpus brain.** Extract recurring concepts and decision rules from the corpus into a machine-readable file. Each concept should include labels, aliases/keywords, source IDs, trigger terms, and practical decision rules.
2. **Use the brain in retrieval.** Expand short questions with matched concept labels/keywords/source IDs so follow-ups can retrieve the right material.
3. **Use the brain in composition.** Pass matched principles into the LLM composer and require application to the user's situation, not quotation alone.
4. **Generalize context resolution.** Resolve follow-ups by matching the primary concept from history; avoid branches like `if topic == micromanagement`.
5. **Filter displayed sources.** The UI should only show cited/materially used sources, not every retrieved chunk. Test semicolon/comma/title-year citation variants.
6. **Replace snippet fallback.** If the model is unreachable, respond that the composer is unavailable and show relevant sources; do not impersonate from concatenated snippets.
7. **Evaluate conversations.** Add scripted product probes that inspect the actual answer, resolved question, concepts, retrieved source IDs, and displayed source IDs.

## Good probe set

- Direct known-source: “does Ben have a blog on micromanaging?”
- Follow-up with pronoun/context: “what if the person is senior?” after a micromanagement turn.
- Practical synthesis: “I hired an exec from a big company and the team hates the process he brought. What should I do?”
- Trap/current silence: ask about a current event or private person not covered by corpus.
- Source alignment: answer cites one source while retrieval returns several; UI should show only the cited/materially used source(s).

## Product-grade verdict criteria

Pass only if the answer:

- Feels like direct first-person advice from the intended persona contract.
- Uses corpus-derived rules/tradeoffs to reason.
- Distinguishes citations from synthesized judgment.
- Refuses or narrows when the corpus is silent.
- Keeps multi-turn context without one-off hacks.

Do not count health checks, HTTP 200s, or passing unit tests as sufficient product acceptance for persona quality.
