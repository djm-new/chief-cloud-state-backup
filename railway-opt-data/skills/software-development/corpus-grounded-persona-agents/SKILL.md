---
name: corpus-grounded-persona-agents
description: "Build, repair, and validate private persona/chat agents that reason from a sourced corpus instead of stitching snippets. Covers corpus brain/worldview extraction, grounded inference, follow-up context, citation alignment, fallbacks, and product-grade conversation probes."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [persona-agent, rag, grounded-reasoning, corpus-brain, citations, conversation-eval]
    related_skills: [public-corpus-ingestion, dspy, dogfood, requesting-code-review, railway-app-deployment]
---

# Corpus-Grounded Persona Agents

## Overview

Use this skill for private agents that answer in the voice or worldview of a person/organization using a verified corpus: public writings, interviews, talks, podcasts, books the user provided, internal docs, or a curated knowledge base.

The core failure mode is building a technically healthy RAG app that behaves like a dumb snippet-stitcher. A persona agent must preserve the corpus as evidence, but also reason from the corpus's principles, decision rules, and worldview. Endpoint health, retrieval hits, and source cards are not sufficient evidence that the product works.

## When to Use

- Building or repairing a corpus-backed persona/advisor/chat agent.
- User says the bot is not smart enough, generic, extractive, or not behaving like the source person.
- Turning a Phase A corpus into a reasoning agent/runtime.
- Adding multi-turn memory, grounded inference, citation filtering, persona prompts, or answer-quality evaluation.
- Validating the deployed chat experience, not just tests or health checks.

Load related skills as needed:
- `public-corpus-ingestion` for corpus/bibliography acquisition and coverage.
- `dspy` for modular RAG/reasoning pipelines and optimization.
- `dogfood` for browser-level product QA.
- `requesting-code-review` before commits with nontrivial code changes.
- `railway-app-deployment` for production deploy verification.

## Product Standard

A working persona agent must pass all three layers:

1. **Infrastructure-grade:** app boots, health checks pass, env vars set, retrieval returns chunks.
2. **Evidence-grade:** answers cite actual sources, UI sources match cited sources, unsupported claims are refused or qualified.
3. **Reasoning-grade:** the answer applies corpus-derived principles to the user's situation in a direct, useful way while distinguishing citation, synthesis, and speculation.

Do not call the work done until a live or scripted multi-turn conversation demonstrates reasoning-grade behavior.

## Architecture Pattern

### 1. Keep RAG, but add a corpus brain

RAG gives local evidence. Add a structured `corpus_brain` layer that captures global principles:

```json
{
  "id": "task-relevant-maturity",
  "label": "Task Relevant Maturity",
  "summary": "How much direction a manager should give depends on the task and person's maturity on that task, not on generic seniority.",
  "decision_rules": [
    "Diagnose the task before prescribing management style.",
    "Low maturity for this task needs more instruction; high maturity needs context and goals."
  ],
  "keywords": ["task relevant maturity", "micromanagement", "delegation"],
  "source_ids": ["2010-04-05-on-micromanagement"]
}
```

The brain should be generated/expanded from the whole corpus, not hand-coded around one demo question. Include principles, tradeoffs, counterexamples, trigger terms, and source IDs.

### 2. Compose with inference, not snippets

The composer prompt should require the model to:

- Answer in first person only if the product contract asks for persona simulation.
- Start from retrieved evidence and matched brain concepts.
- Apply decision rules to the user's situation.
- Cite source titles/years for substantive claims.
- Clearly separate direct source evidence from synthesized judgment.
- Say the corpus is silent when evidence is weak.

Avoid deterministic fallback answers that concatenate retrieved snippets. If the LLM composer is unavailable, return a graceful grounded-unavailable response plus relevant source titles, not a fake persona answer.

### 3. Preserve multi-turn context

Short follow-ups like “what about if the person is senior?” often need the prior topic. Send recent chat history to the backend and resolve follow-ups before retrieval:

- Identify the primary concept/entity in recent turns.
- Rewrite the new user message into a standalone question.
- Expand retrieval queries with concept labels, keywords, and source IDs.
- Keep this generic; do not hard-code one topic like micromanagement.

### 4. Align displayed sources to actual citations

Do not show every retrieved source as if it supported the final answer. Filter UI source cards to sources actually cited or materially used by the composer. Handle common citation separators such as commas, semicolons, brackets, and title/year variants.

### 5. Track unsupported claims

Add a post-check or evaluator that inspects the answer against retrieved chunks and brain concepts:

- Supported: claim traces to source text or a recorded decision rule with source IDs.
- Synthesized: claim is an inference from multiple sources and is labeled as such.
- Unsupported: claim should be removed, regenerated, or qualified.

## Repair Workflow for “Not Smart Enough” Feedback

When the user says the agent is dumb, generic, snippet-glue, or not reasoning:

1. **Acknowledge product failure, not just implementation bugs.** The issue is answer quality and reasoning, even if the endpoint is healthy.
2. **Capture failing conversations.** Save the user question, bot answer, retrieved chunks, prompt/model, cited sources, and UI source list.
3. **Classify the failure:** retrieval miss, missing corpus concept, composer prompt too extractive, no follow-up context, source display mismatch, fallback path, or model quality/cost issue.
4. **Inspect corpus coverage for the topic.** Verify whether the relevant source exists and whether the retriever can find it.
5. **Add/expand corpus brain concepts.** Prefer an automated scan of the whole corpus for recurring principles, then hand-review the concepts.
6. **Refactor composer for grounded inference.** Make the answer apply rules and tradeoffs to the user's actual situation.
7. **Generalize follow-up logic.** Resolve pronouns/topics through concept matching, not one-off string checks.
8. **Filter citations/sources.** Ensure displayed sources match what the answer cited.
9. **Test.** Add unit tests for concept matching, follow-up rewriting, fallback behavior, and source filtering.
10. **Run product probes.** Use realistic multi-turn questions; inspect the actual returned answer and source cards.
11. **Deploy and verify live.** Confirm the deployed URL uses the new env/model/version and run at least one live conversation through the UI/API.

## Product Interaction Eval

Create a script for repeatable chat probes, not just pytest. Minimum scenarios:

- Direct known-source question.
- Ambiguous follow-up requiring history.
- Practical advice question requiring synthesized application of principles.
- Out-of-corpus/current-event trap requiring grounded refusal.
- Citation/source-card alignment check.
- Composer-unavailable fallback check.

For each probe, record:

- Request and history.
- Resolved question/query expansion.
- Matched brain concepts.
- Retrieved source IDs.
- Final answer.
- Displayed source IDs.
- Verdict and failure reason.

## Acceptance Checklist

- [ ] Corpus brain covers the major recurring concepts, not just the latest failing prompt.
- [ ] Retrieval uses both the user question and matched corpus-brain concepts.
- [ ] Backend accepts and uses recent conversation history.
- [ ] Composer produces synthesized grounded advice, not pasted excerpts.
- [ ] Fallback path does not impersonate or snippet-stitch when the model is unreachable.
- [ ] UI displayed sources are a subset of cited/materially used sources.
- [ ] Unit/integration tests cover brain matching, follow-up resolution, citation filtering, and fallback.
- [ ] Product interaction eval includes multi-turn and out-of-corpus cases.
- [ ] Live deployed conversation was inspected before saying done.

## Pitfalls

1. **Health-check false confidence:** a green deployment says nothing about persona intelligence.
2. **Retriever-only worldview:** top-k local chunks cannot substitute for global principles learned from the whole corpus.
3. **One-demo hard-coding:** fixing only the user's example makes the bot look better for one question and dumb elsewhere.
4. **Source-card overclaiming:** retrieved-but-uncited cards imply support the answer may not have used.
5. **Fallback impersonation:** deterministic fallback snippets can look like low-quality persona reasoning. Be honest when the model is unavailable.
6. **Generic MBA advice:** if an answer could be given without the corpus, it is probably failing the product goal.
7. **No live probe:** tests pass can still hide a bad chat UX; inspect actual product output.

## Support Files

- `references/ben-bot-reasoning-repair.md` records a condensed case study of repairing a Ben Horowitz corpus agent from snippet-stitching toward corpus-conditioned inference.
