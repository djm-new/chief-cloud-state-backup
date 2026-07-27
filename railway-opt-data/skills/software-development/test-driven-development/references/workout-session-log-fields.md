# Workout session log fields

Use this pattern when a form has both planned and actual workout values:

- `prescribedReps` / `prescribedWeightLb`: what the workout asked for
- `actualReps` / `actualWeightLb`: what the user actually did
- UI should show the target as a placeholder or helper label when the actual value is expected to be entered manually
- progress/repeat logic should consume `actual*` values only

## Example behavior

- A set prescribed for 5 reps can be saved as 4 reps if the lifter fails early.
- The next-session recommendation should repeat the same weight when any working set falls short of the target.
- New session drafts should not auto-populate `actualReps` from the prescription; leave it blank until the user logs the set.
