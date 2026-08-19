# HealthOS workout seed schema notes

This reference captures the minimal contract used by the HealthOS workout program seed.

## Required top-level keys

- `programName`: display name of the program.
- `status`: seed status flag used by the app.
- `philosophy`: object with goal/principles/note.
- `defaults`: global rules such as unit and progression behavior.
- `workouts`: ordered list of workout days.

## Workout object

Each workout should preserve source order and typically includes:

- `name`: human-readable workout title.
- `emphasis`: short summary for preview cards.
- `exercises`: ordered list of exercise objects.

## Exercise shapes currently supported by HealthOS

- Rep range:
  - `name`
  - `type`
  - `sets`
  - `repRange: { min, max }`
  - `notes`
- Fixed reps:
  - `name`
  - `type`
  - `sets`
  - `reps`
  - `notes`
- Side-specific work:
  - `name`
  - `type`
  - `sets`
  - `repsPerSide`
  - `notes`
- Distance work:
  - `name`
  - `type`
  - `sets`
  - `distance: { value, unit }`
  - `notes`

## Session drafting behavior to remember

- Rep-range prescriptions are drafted with the upper bound as the initial target rep count.
- Fixed-rep and per-side exercises draft with their explicit target rep count.
- Distance-based work should keep the distance object intact for display and persistence.
- Workout preview and live logging render exercises in source order.

## Useful import/update rule

When importing a new workout plan, translate its pairing/rest/tempo language into `notes` so the app can preserve the coaching intent without adding extra runtime logic.
