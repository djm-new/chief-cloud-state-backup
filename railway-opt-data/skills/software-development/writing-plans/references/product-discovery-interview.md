# Product Discovery Interview Mode

Use when the user wants to design a product/workflow but has not approved implementation yet, especially when they say a large questionnaire is too much friction or ask for "BMAD-style".

## Pattern

1. **Confirm no-build mode.** State that you will not create files, code, jobs, or integrations until the design is approved.
2. **Ask one short question at a time.** Prefer 2-4 labeled options plus room for freeform answers.
3. **Translate each answer into a product decision.** Start the next turn with a one- or two-line lock-in: "Good. That means X."
4. **Avoid scroll-friction.** Do not dump 20 questions at once. The user should not need to scroll up and answer a list.
5. **Periodically report progress.** If the interview is long, say roughly how far through discovery you are and what remains.
6. **Synthesize before build.** Once enough decisions are made, produce a PRD/spec with open questions and ask for approval before implementation.

## Good question style

- "Which is primary: gym logging, meal logging, dashboard, or all?"
- "For meal logging: exact database, manual macros, LLM estimate, or hybrid?"
- "For progression: app recommends next weight, tracks only, or recommends with override?"

## Pitfalls

- Do not ask a giant questionnaire after the user requests low-friction interview mode.
- Do not turn product discovery into implementation planning too early.
- Do not treat a user's answer as a final spec silently; summarize the implication so they can correct it.
- If the user says "don't make anything before aligned," do not create code, repos, apps, automations, or recurring jobs. Skill/library updates requested by the user are okay.
