---
name: healthos-development
description: "Use when changing HealthOS app behavior, workout programs, seed data, meal logging, dashboard UX, API routes, or deployment-facing product code. Covers current-code confirmation, data-path tracing, workout seed contracts, tests, and live-vs-local verification."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [health, healthos, product, workouts, meals, seed-data, nextjs, testing]
    related_skills: [systematic-debugging, test-driven-development, railway-app-deployment]
---

# HealthOS Development

## Overview

Use this umbrella skill for HealthOS product/code work: meal logging, daily ledger/history, dashboard and health-metric UX, API route behavior, workout program seed imports, workout-session helpers, and tests that pin HealthOS behavior.

HealthOS work should be **current-state-first** and **contract-preserving**. Inspect the relevant code paths before accepting a reported behavior as true, make the smallest behavior change that preserves the existing data model, and clearly distinguish local code readiness from deployed/live completion.

## When to Use

Use for:

- HealthOS meal logging, meal editing, macro estimates, quick re-log/favorite/frequent meals.
- Daily ledger/history, dashboard cards, body metrics, calories/TDEE, sleep, steps, and Apple Watch inputs.
- UI/UX flow changes, app routes, and API routes for HealthOS behavior.
- Editing or importing workout programs and seed JSON.
- Changing workout names, exercise order, prescriptions, workout display, live workout logging, or workout tests.
- Adding workout helpers such as barbell plate calculators.

Do not use for generic fitness advice unless it is being translated into the HealthOS app/data model.

## Required Workflow for App Behavior Changes

1. **Confirm the user's understanding from code before implementing.**
   - If DJ says “currently X,” inspect the relevant source files and state whether X is code-confirmed, contradicted, or ambiguous.
   - Avoid saying “understood” in a way that implies verified behavior unless code has been read.
   - If DJ explicitly asks for evaluation before writing, do not edit files until after reporting the code-confirmed current behavior and proposed approach.

2. **Trace the full data path, not just the visible component.**
   - Identify the page/server component that loads data.
   - Identify helper libraries that shape the data.
   - Identify client components that render or mutate it.
   - Identify API route(s) called by the client.
   - Identify Prisma model fields or seed structures that constrain implementation.

3. **Evaluate the minimal behavior change.**
   - Prefer changing the data-source/helper layer when the UI already renders a generic list of choices.
   - Preserve existing payload shapes unless the feature truly needs new fields.
   - Keep deleted/soft-deleted data excluded when existing behavior excludes it.
   - Preserve existing date semantics (`app-time` helpers) for meal/day logging.

4. **Clarify product semantics before coding when they affect data meaning.**
   Ask or state a recommendation for choices like:
   - whether “meal” means exact description only or normalized description;
   - whether quick re-log should use latest corrected macros, averaged macros, or original macros;
   - whether ranking is all-time, rolling window, or category-specific;
   - tie-breakers such as most recent logged time.

5. **Implement with tests when logic changes.**
   - Extract pure ranking/formatting helpers if needed so unit tests do not require a database.
   - Add tests for normalization, deleted-data exclusion where practical, limits, and tie-breakers.
   - Run typecheck and relevant tests before reporting completion.

6. **Distinguish local implementation from live completion.**
   - If DJ is reporting behavior from production, do not say the user-facing change is “implemented” until it is committed, pushed/deployed, and the live UI is verified.
   - Use a visible marker from the change (label text, unique copy, or route output) to prove the live app is serving the new build.
   - If only local code changed, say “local commit/code is ready.”
   - Do not stop at the first stale credential or unauthenticated CLI result. For HealthOS, GitHub is the source of truth and Railway is the runtime; search existing durable credential stores/state backups, validate candidates without printing secrets, push the commit, and then verify production before asking DJ for access.

7. **Treat screenshots as live-state evidence.**
   If DJ sends a screenshot after a UI change, inspect visible labels/copy against the intended marker. A screenshot still showing old copy means the live app has not updated or the user is on a stale build.

## Meal and Daily-Ledger Patterns

### HealthOS meal quick-log/re-log map

For the inspected quick re-log flow:

- Today page: `app/(app)/page.tsx`
  - Loads quick tray data and passes it to `DailyMealsLedger`.
- Data helper: `lib/recent-meals.ts`
  - Previously implemented most-recent distinct meals using `orderBy: { loggedAt: 'desc' }`, `take: 80`, and normalized descriptions for de-duping.
- UI component: `components/meals/DailyMealsLedger.tsx`
  - Renders the “Quick re-log” chip row.
  - Calls `/api/meals/relog` with description/macros and selected `dateKey`.
- API route: `app/api/meals/relog/route.ts`
  - Creates a new `Meal` without re-running LLM estimation.
- Prisma model: `prisma/schema.prisma` model `Meal`
  - Key fields: `userId`, `date`, `mealCategory`, `loggedAt`, `description`, `calories`, `proteinG`, `carbsG`, `fatG`, `deletedAt`.

### Frequent-meal tray pattern

For a “top N most frequently logged meals” tray:

1. Query non-deleted meals for the current user.
2. Normalize descriptions with `description.trim().toLowerCase()` for grouping, matching prior distinct behavior.
3. Count occurrences per normalized description.
4. Keep the latest logged meal within each group as the re-log payload, so edited/corrected later entries win.
5. Sort by count descending, then latest `loggedAt` descending as a tie-breaker.
6. Return the requested limit, e.g. top 5 instead of the previous 6 when requested.

Prefer TypeScript aggregation when normalized grouping matters; Prisma `groupBy` on raw `description` would split case/whitespace variants.

## Workout Program and Seed Workflow

HealthOS is a *neutral tracker* for an approved training plan. Preserve the user’s program intent, but keep stored data normalized and consistent across seed copies and session helpers.

### Treat the seed as a pair

Update both unless the repo intentionally diverges:

- `/opt/data/projects/healthos/docs/INITIAL_PROGRAM_SEED.json`
- `/opt/data/projects/healthos/INITIAL_PROGRAM_SEED.json`

Keep them byte-for-byte aligned.

### Preserve the program contract

- `programName`, `status`, `philosophy`, `defaults`, and `workouts` should remain present.
- Workout ordering matters because the app uses index-based `day-N` routing.
- Exercise ordering matters because preview/session screens render in source order.

### Normalize exercise prescriptions into supported shapes

Use the shapes HealthOS already understands:

- `repRange` for target ranges.
- `reps` for fixed targets.
- `repsPerSide` for unilateral skills.
- `distance` for carries.

Keep `notes` concise but useful; include pairing/rest/density cues there when the workout depends on them.

### Update session expectations with the seed

If exercise order or prescription shape changes, update unit tests that assert draft structure. Pay special attention to:

- `tests/unit/workout-session.test.ts`
- progression/preview helpers if a shape is newly introduced
- `buildSeedWorkoutSessionDraft()`
- `formatExercisePrescription()`

### Verify structural consistency

- Validate both JSON files parse.
- Validate both copies match.
- Validate workout count/order and exercise count/order.
- Validate any new exercise shape is represented in session helpers and preview formatting.

See supporting files:

- `references/seed-schema.md`
- `references/workout-completion.md`
- `scripts/validate_workout_seed.py`

## Workout Completion Payloads

Completion payloads represent *what was logged*, not proof every prescribed exercise was finished.

Rules:

- Missing exercises/sets mean “skipped / not logged,” not “invalid payload.”
- Completion validation should be permissive: `exercises` defaults to `[]`, and each exercise’s `sets` defaults to `[]`.
- Merge submitted completion payloads with the persisted session before summarizing totals.
- Keep skipped exercises incomplete, preserve the existing session rows, and compute completed volume from the merged structure.

## Barbell Plate Calculators

When adding a plate-loading helper:

1. Keep logic split into:
   - `lib/` math returning structured results (`exact`, `perSideWeightLb`, `platesPerSide`, `message`);
   - a small client component that renders the result and keeps the input editable.
2. Default to a **45 lb bar** and surface that assumption in the UI.
3. Use a descending greedy pass over plate sizes so the result uses the fewest plates.
4. Keep plate counts **per side**.
5. If the requested total cannot be loaded exactly, return a helpful message instead of a guessed approximation.
6. Gate UI to barbell exercise contexts (for example `barbell_` exercise types); do not place it on the top-level workouts index.
7. Add a small unit test for a common exact total and one invalid/non-exact case.

See supporting files:

- `references/barbell-loading.md`
- `references/barbell-plate-calculator.md`

## Common Pitfalls

1. **Parroting user-reported behavior as verified.** Inspect code before claiming current behavior.
2. **Writing before evaluation when asked not to.** Respect current-state-first evaluation requests.
3. **Only reading the component.** HealthOS behavior often spans server page data loading, helpers, client components, API routes, and Prisma models.
4. **Breaking quick re-log by changing payload shape.** If only tray ranking changes, preserve the description/macro payload and API route.
5. **Forgetting soft-delete semantics.** Meal lists and quick logging should exclude `deletedAt != null` unless explicitly requested otherwise.
6. **Changing labels without behavior.** If a tray switches from recent to frequent, update names/comments/labels so future maintainers understand the source.
7. **Updating only one seed file.** HealthOS keeps a docs copy and root mirror.
8. **Changing exercise order without updating tests.** Session draft tests often assert positional exercises.
9. **Using a new prescription shape without plumbing it through helpers.** The plan can parse yet display incorrectly.
10. **Rejecting partial workout completion.** Completion payloads should tolerate skipped exercises.
11. **Losing pairing/rest intent.** Capture workout organization in `notes`.
12. **Putting helper UI on the wrong page.** Barbell calculators belong on barbell exercise surfaces, not the workouts index.
13. **Making program logic coach-y instead of tracker-neutral.** Store the plan faithfully; avoid adding training decisions unless product explicitly needs them.

## Verification Checklist

- [ ] Current behavior confirmed from source paths, not just user report.
- [ ] Data path traced: page → helper → component → API → Prisma/seed model.
- [ ] Product semantics/tie-breakers documented or clarified.
- [ ] Minimal code change identified before editing.
- [ ] Tests added/updated for changed ranking, data-shaping, seed, or session behavior.
- [ ] Both seed JSON files updated and identical when workout seed changes.
- [ ] JSON parses cleanly.
- [ ] Workout count/order and exercise order match the intended plan.
- [ ] New exercise shapes are supported by session helpers and preview formatting.
- [ ] Any barbell-only helper UI is gated to barbell exercises and not shown on the workouts index.
- [ ] `npm run typecheck` passes when Node/npm is available.
- [ ] Relevant unit/Vitest tests pass when Node/npm is available.
- [ ] Local implementation status is clearly distinguished from production/live status.
- [ ] If production/live behavior matters, deployed UI/API was verified with a unique marker or real app action.
