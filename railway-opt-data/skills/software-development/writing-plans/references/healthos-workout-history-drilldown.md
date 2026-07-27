# HealthOS workout history drill-down

## Reusable lesson

For workout analytics/history work, keep the live in-workout logger untouched when possible.

Preferred pattern:
- Reuse completed `workoutSession` + `SetSession` data already in the database.
- Build a read-only drill-down route per exercise.
- Use stable slugification for exercise names in URLs.
- Show both per-session progression and the full set log.
- Fall back gracefully when a lift has history but not enough completed working sets for a strength summary.

## Good route shape

- `/workouts` = overview + status cards
- `/workouts/exercise/[exerciseSlug]` = drill-down for one exercise

## Data to show

- Session date
- Top working set per session
- Estimated 1RM trend
- Full set-by-set history
- Prescribed vs actual weight/reps

## Pitfall

Do not make the drill-down depend on the live logger UI state. It should render from persisted completed sessions only.