# Barbell plate calculator placement

Use this when adding plate-loading helpers to HealthOS workout flows.

## Placement rule
- Show the calculator only in *barbell-based exercise contexts*.
- Do **not** place it on the top-level workouts index/list.
- Good placements:
  - workout preview cards for barbell exercises
  - live workout screen for the active barbell exercise

## Barbell detection
- Treat exercise types with the `barbell_` prefix as barbell-based.
- Keep the predicate centralized in `lib/program-seed.ts` (or the equivalent seed helper), rather than re-implementing the check in multiple UI files.

## UX notes
- The calculator should be a helper attached to the exercise card, not a global workout-page widget.
- Seed/recommendation weight can be used as the initial total weight when available.
- Keep the widget usable even when no recommendation exists by falling back to a sensible default.

## Verification
- Barbell exercises render the calculator.
- Dumbbell/bodyweight/conditioning exercises do not.
- The workouts index remains uncluttered.
