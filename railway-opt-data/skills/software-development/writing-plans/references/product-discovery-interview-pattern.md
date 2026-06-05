# Product Discovery Interview Pattern — Health/Dashboard Apps

Use this reference when planning a personal dashboard/tracking app with the user before implementation.

## When it applies

- User has a broad product idea and explicitly wants alignment before build.
- The product has multiple daily capture surfaces (e.g., dashboard, food logging, workout logging).
- The user reacts poorly to long questionnaires and asks for an interview / BMAD-style cadence.

## Interview cadence

1. Ask one short question at a time.
2. Use compact A/B/C/D choices when useful.
3. After each answer, summarize the decision in 1-2 lines.
4. Immediately ask the next high-leverage question.
5. When the decision space is ~80% clear, stop interviewing and synthesize a spec.
6. Do not build until the user explicitly says to go forward.

## High-leverage decision order

1. Primary surfaces / usage moments.
2. Logging friction vs precision.
3. Data sources and manual vs automated import.
4. Core metrics and rolling-window calculations.
5. Program/schema flexibility if workout or task tracking is involved.
6. Data integrity: editability, deletion, audit log, backups.
7. Platform/deployment/auth decisions.
8. Source control and backup posture.
9. Initial seed data/programs/goals.
10. Open blockers before implementation.

## HealthOS-specific reusable lessons

- For dashboard apps, distinguish daily capture UX from analytics richness: capture must be simple; analysis can be rich.
- Rolling 7-day windows can be more useful than calendar weeks for health/workout adherence.
- If the user wants app design and expert coaching, keep the app neutral: Hermes can critique/design programs separately, while the app tracks approved programs.
- For workout trackers, do not assume fixed reps only. Support fixed reps, rep ranges, per-side work, timed/distance carries, conditioning sets, and warm-up sets.
- For food logging, if speed is preferred: save LLM estimates immediately with Edit/Undo rather than requiring an approval step or showing confidence labels.
- For data ownership: primary DB can be structured/durable while Google Sheets acts as human-readable backup/export, not runtime DB.

## Spec artifact shape

Create a saved Markdown spec with:

- Product thesis
- Locked decisions
- Primary product surfaces
- Metrics definitions
- Data model
- Integrations plan
- Backup/export plan
- Initial screen map
- UX principles
- Build sequence
- Open questions
- Non-goals
- Definition of done
