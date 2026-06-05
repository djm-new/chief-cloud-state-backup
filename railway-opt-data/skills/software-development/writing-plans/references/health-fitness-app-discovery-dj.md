# Health & Fitness App Discovery Notes

Use as a reference when planning DJ's personal health/exercise dashboard. These are product preferences from discovery, not an implementation log.

## Product posture

- Do not build before alignment; produce spec/mockups first.
- Once DJ says to go forward on an active project, stop waiting for repeated prompts: synthesize, scaffold, verify, commit, and keep pushing until the current phase is done or blocked by external credentials/approval.
- Mobile-first PWA/web app first, desktop dashboard included, deployed with private passcode/login.
- Replace the existing Replit app rather than evolve it.
- Clean/simple UI; show 2-3 mockup directions before final visual commitment.
- Primary surfaces: Today/dashboard, meal logging, gym mode.

## Technical/deployment posture

- Working name/repo: `healthos`.
- Repo should be a private repo under DJ's personal GitHub.
- Hosting should be Railway in the Chief ecosystem.
- Use PostgreSQL on Railway for primary app data.
- Initial auth: username/password for DJ, no public signup.
- Code should be committed/pushed from the start; GitHub backs up code, while Google Sheets backs up app data.
- Google Sheets backup should be owned by DJ's personal Google account (`dj.mauch@gmail.com`).
- If GitHub/Railway CLIs are unauthenticated, keep building locally, commit progress, and record the auth blocker rather than stopping the project.

## Today/dashboard priorities

- Balanced rolling 7-day status dashboard at top.
- Workouts last 7 days: default target 4 workouts / rolling 7 days.
- 7-day calorie balance: show deficit/surplus and estimated pounds gained/lost.
- Weight: manual daily entry, 7-day average.
- Sleep: nightly duration only, 7h/night target, rolling sleep balance; naps do not count.
- Macros: show today and 7-day averages.

## Nutrition

- Hybrid meal logging: text/voice-style descriptions + LLM macro estimate; no photos in v1.
- Speed over accuracy: save immediately with easy edit/undo; no confidence labels in the main flow.
- Track calories, protein, carbs, fat.
- Meal categories: breakfast/lunch/dinner/snack.
- Nutrition targets are manually entered/editable (calories, protein, carbs, fat); app may suggest but does not override.
- Goal history is required; evaluate old days against the goals active at that date. No scheduled future goal changes in v1.

## Calories out / activity

- Track active calories and resting calories, manually copied from Apple Watch initially; fallback to estimated TDEE if missing.
- Steps: manual now, Apple Health import later.
- Store source for imported data; manual overrides supersede imported values.

## Workouts

- Custom program engine; DJ will paste full program into chat and Hermes should parse/import after approval.
- For current HealthOS build-stage seed, use DJ's 3-day strength/athletic-density program even if future program critique/refinement happens separately.
- App should remain a neutral tracker/importer; Hermes can help critique/design programs, but HealthOS should track the program DJ approves rather than hard-code coaching opinions.
- Gym mode should preview full workout before start; start goes to first exercise.
- During workout: active exercise focus + collapsible full checklist; current workout only, no exercise-history clutter.
- Set logging: tap checkmark to accept prescribed reps/weight; quick edit if different.
- Do **not** make DJ enter weight or reps for every set. That is unacceptable workout UX. Use exercise-level working weight as the default for all sets, prefill prescribed reps automatically, and require input only for exceptions/missed reps/manual changes.
- First time for an exercise may have blank working weight; after history exists, start from the last saved/suggested working weight.
- App recommends next weights automatically.
- Default progression: hit all target reps -> +5 lb; miss any target reps -> repeat weight. No automatic deload.
- Seed/current-program progression also needs rep-range logic: for prescriptions like 3x3-5, increase only when all working sets hit the top of the range; otherwise repeat.
- Workout engine must support fixed reps, rep ranges, per-side work, loaded carries by distance/time, and conditioning rep ranges.
- Units: pounds.
- RPE per exercise; post-workout energy/performance/soreness scores.
- Auto-calculate warm-up sets. No rest timers in v1.
- Partial sessions count as workouts; record exactly what was prescribed and what was done.

## Longevity/cardio

- Peter Attia-inspired but lightweight in v1.
- Zone 2 habit: minutes + heart-rate zone, weekly target/checkoff.
- VO2 max trend can be tracked/imported later.
- Grip via carries/hangs as training proxies, not dynamometer.
- No dedicated injury/pain module, no waist/body fat/progress photos in v1.

## Data integrity and backup

- Editable old entries with audit history.
- Deletes allowed; audit log keeps record.
- Primary app database plus Google Sheets backup: one spreadsheet with multiple tabs, including clean tables and separate AuditLog tab.
- Backup nightly plus manual export button.

## Discovery style

DJ prefers fast interview/pitter-patter over giant questionnaires. Ask one decision at a time, summarize the implication, then continue. When enough is known, produce a spec rather than continuing indefinitely.
