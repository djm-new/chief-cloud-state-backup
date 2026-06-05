# HealthOS Workout UX Notes

Use these notes when planning or implementing HealthOS workout logging flows for DJ.

## Core UX principle

Workout logging should be **plan-first and exception-only**:

- The workout starts from the prescribed program.
- Reps should be prefilled from the target prescription.
- Weights should come from the given program weight, the last completed working weight, or the next suggested progression.
- The user should mark sets done with one tap.
- Manual rep/weight entry should be hidden behind an exception/edit affordance, not required for every set.

DJ explicitly rejected entering weight every set/rep and entering reps every set as “silly and absurd UX.” Treat granular entry as a pitfall unless the user explicitly asks for detailed set-by-set editing.

## Preferred interaction model

For each exercise:

1. Show exercise name + prescription.
2. Show one exercise-level “working weight” field.
3. Apply that weight to all sets by default.
4. Show each set as a large tap target, e.g. `Set 1 — 5 reps @ 185 lb`.
5. Tapping a set marks it done using the prefilled planned weight/reps.
6. Provide “Edit this set only” for missed reps, changed weight, or other exceptions.
7. Finish workout saves all completed sets with actualWeightLb/actualReps already populated.

## Progression expectation

Next-session defaults should not merely repeat blanks:

- First choice: program-prescribed or manually configured starting weight.
- Next choice: last completed working weight for that exercise.
- Future improvement: if all target reps were hit, suggest `+5 lb`; if any target was missed, repeat the weight.

## Implementation pattern used in HealthOS

- `lib/workout-session.ts`: build session drafts with `actualReps` initialized from `prescribedReps` and `actualWeightLb` initialized from starting/prior weight.
- `app/api/workouts/sessions/route.ts`: fetch recent completed exercise sessions for the user, map exercise name -> last actual working weight, and pass those into the draft builder.
- `components/workouts/LiveWorkout.tsx`: expose one exercise-level working weight input, one-tap set completion, and hide per-set weight/reps behind “Edit this set only.”

## Pitfalls

- Do not make the database model shape leak into the gym UI. Even if `SetSession` stores actual weight/reps per set, the UI should not require typing them per set.
- Do not require reps entry when the user completed the prescribed work. Prefill target reps and only edit misses.
- Do not force weight entry repeatedly. One exercise-level weight is sufficient for the common case.
- For unilateral or distance/carry exercises, keep the same principle: default from the prescription, edit only exceptions.