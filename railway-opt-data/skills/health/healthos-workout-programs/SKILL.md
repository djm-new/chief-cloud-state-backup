---
name: healthos-workout-programs
description: Use when editing or importing HealthOS workout programs, seed JSON, or workout-prescription tests. Keeps program structure, session drafting, and validation aligned across copies.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [health, fitness, workout, healthos, seed-data, testing]
    related_skills: [software-development:hermes-agent-skill-authoring]
---

# HealthOS Workout Programs

## Overview

Use this skill when you need to update HealthOS workout programming: the seed JSON, the program display, live workout logging expectations, or the tests that pin the workout structure.

The key idea is that HealthOS is a *neutral tracker* for an approved training plan. Preserve the user’s program intent, but keep the app’s stored data normalized and consistent across the two seed JSON copies and the session helpers that consume them.

## When to Use

- Editing `INITIAL_PROGRAM_SEED.json` or `docs/INITIAL_PROGRAM_SEED.json`
- Changing workout names, exercise order, sets/reps, or notes
- Importing a new 3-day / split / template-based program into HealthOS
- Updating workout-session tests or seed-drafting logic
- Adding support for a new prescription shape such as:
  - `repRange`
  - fixed `reps`
  - `repsPerSide`
  - `distance`

Do *not* use this skill for generic fitness advice; it is specifically for the HealthOS data model and the program seed workflow.

## Core workflow

1. **Treat the seed as a pair, not a single file.**
   - Update both:
     - `/opt/data/projects/healthos/docs/INITIAL_PROGRAM_SEED.json`
     - `/opt/data/projects/healthos/INITIAL_PROGRAM_SEED.json`
   - Keep them byte-for-byte aligned unless the repo intentionally diverges.

2. **Preserve the program contract.**
   - `programName`, `status`, `philosophy`, `defaults`, and `workouts` should remain present.
   - Workout ordering matters because the app uses index-based `day-N` routing.
   - Exercise ordering matters because preview/session screens render in source order.

3. **Normalize exercises into the shapes HealthOS already understands.**
   - Use `repRange` for target ranges.
   - Use `reps` for fixed targets.
   - Use `repsPerSide` for unilateral skills.
   - Use `distance` for carries.
   - Keep `notes` concise but useful; include pairing/rest cues there if the workout depends on them.

4. **Update the session expectations together with the seed.**
   - If the exercise order or prescription shape changes, update the unit tests that assert draft structure.
   - If the change affects workout completion, verify the API still accepts partial logging when the user skips exercises.
   - Pay special attention to:
     - `tests/unit/workout-session.test.ts`
     - any progression/preview helpers if the shape is newly introduced

5. **Verify structural consistency.**
   - Validate that both JSON files parse.
   - Validate that both copies match.
   - Validate the expected exercise count/order for each workout.
   - Validate any new exercise shape is represented in `buildSeedWorkoutSessionDraft()` and `formatExercisePrescription()` if needed.

## Seed structure rules

### Program-level guidance

- Keep the app-facing wording neutral and tracker-oriented.
- Put coaching flavor into `notes`, not into hidden logic.
- If the user provides a specific density block, pairing, or time cap, preserve it in `notes` so preview screens show the intended structure.

### Exercise mapping

- `repRange` → used for rep-range exercises; the app records the top end as the target working reps.
- `reps` → used for fixed-rep prescriptions.
- `repsPerSide` → used for side-specific movements like Turkish get-ups or unilateral carries.
- `distance` → used for loaded carries and other distance-based work.

### Common exercise-data pitfalls

- Don’t collapse distinct movements into one generic row if the workout intentionally separates them.
- Don’t reorder exercises just to make them “look” nicer; the source order is the workout order.
- Don’t forget to update the tests when changing the seed; the tests are part of the contract.

## Recommended update sequence

1. Edit the source workout plan.
2. Translate it into HealthOS seed JSON.
3. Mirror the same change into the root seed file.
4. Update tests that lock the first workout or exercise shape.
5. Run the seed validator script.
6. Re-read the workout preview/session helpers if the new plan uses a prescription shape not previously present.

## Supporting files

- `references/seed-schema.md` — concise schema notes for workout/program imports.
- `references/workout-completion.md` — permissive completion payload rules and merge behavior for skipped exercises.
- `references/barbell-plate-calculator.md` — placement rules and barbell-gating notes for plate-loading helpers.
- `scripts/validate_workout_seed.py` — deterministic validator for the seed pair and workout ordering.


## Barbell plate-loading calculators

When adding a plate calculator to HealthOS, keep the logic split into two layers:

1. `lib/` math that returns a structured result (`exact`, `perSideWeightLb`, `platesPerSide`, `message`).
2. A small client component that renders the result and keeps the input editable.

Implementation notes:

- Default to a **45 lb bar** and surface that assumption in the UI.
- Use a **descending greedy pass** over plate sizes so the result uses the fewest plates.
- Keep plate counts **per side**; don’t ask users to mentally split the bar.
- If the requested total can’t be loaded exactly, return a helpful message instead of a guessed approximation.
- Add a small unit test for a common exact total and one invalid/non-exact case.

## Common Pitfalls

1. **Updating only one seed file.**
   HealthOS currently keeps a docs copy and a root mirror. Both need the same content.

2. **Changing exercise order without updating tests.**
   The session draft test often asserts positional exercises like the first bench movement or a later accessory.

3. **Using a new prescription shape without plumbing it through the session helpers.**
   If the UI or persistence layer doesn’t know the shape, the plan will display incorrectly even if the JSON parses.

4. **Rejecting partial workout completion.**
   Completion payloads should tolerate skipped exercises by treating missing exercises/sets as omitted logging data. Merge submitted data with the persisted session before computing totals.

5. **Losing the pairing/rest intent.**
   If a workout is organized as supersets or density pairings, capture that in `notes` so the preview and live workout screens preserve the training intent.

6. **Putting helper UI on the wrong page.**
   Barbell plate calculators belong on barbell exercise surfaces, not the general workouts index. Gate them off the exercise type (e.g. `barbell_` prefix) and render them only in workout preview/live contexts for the active barbell exercise.

7. **Making the program logic coach-y instead of tracker-neutral.**
   Store the plan faithfully; avoid embedding extra training decisions in code unless the product explicitly needs them.

## Verification checklist

- [ ] Both seed JSON files updated and identical
- [ ] JSON parses cleanly
- [ ] Workout count/order matches the intended split
- [ ] Exercise order matches the source plan
- [ ] Tests updated for any changed exercise positions or prescriptions
- [ ] Seed validator script passes
- [ ] New exercise shapes are supported by the session helpers and preview formatting
- [ ] Any barbell-only helper UI is gated to barbell exercises and not shown on the workouts index
