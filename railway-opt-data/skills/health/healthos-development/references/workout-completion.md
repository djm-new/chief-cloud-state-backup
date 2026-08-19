# Workout completion payloads

## Why this matters

HealthOS must allow a workout session to be saved even when the user skips one or more exercises. The completion payload should represent *what was logged*, not enforce that every prescribed exercise was finished.

## Observed failure mode

- UI sent a valid partial completion payload
- API rejected it with `Invalid workout completion payload`
- Root cause: completion validation required `exercises` and `sets` arrays to be fully present

## Fix pattern

1. Make completion validation permissive:
   - `exercises` defaults to `[]`
   - each exercise’s `sets` defaults to `[]`
2. Merge the submitted completion payload with the persisted session before summarizing totals:
   - keep skipped exercises as incomplete
   - preserve the session’s existing exercise/set rows
3. Update only the exercises/sets the user actually submitted
4. Compute completed volume from the merged structure, not the sparse submission

## Practical rule

- *Missing* exercises/sets mean “skipped / not logged,” not “invalid payload.”
- The save action should succeed as long as the payload references real session IDs and the request is otherwise well-formed.
