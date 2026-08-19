# Daily ToM sync mechanics (daily-tom-sync.py)

How DJ's "DM Running Daily ToM" Google Doc rollover actually works, and the bugs/quirks found while debugging why manual additions "didn't carry over" and why later sections duplicated (2026-07-17, 2026-08-17).

## Pipeline
- Cron job "Daily ToM sync at 5AM ET" → wrapper `/opt/data/scripts/daily-tom-daily-5am-et.sh` (DST-safe, no-ops outside 5AM ET, once-per-day guard via `last_5am_et_run_date`).
- Wrapper runs `/opt/data/scripts/daily-tom-sync.py --date <today> --apply` with `/opt/data/google-accounts/.venv/bin/python` (sandbox/system python lacks the `google` libs).
- Doc: "DM Running Daily ToM", `DOC_ID 10KsXkvIR0Je4J_dGkv0PI-4Mngb5db3MSstjnEU8Gpw`, personal Google account (`/opt/data/google-accounts/personal/google_token.json`).
- State: `/opt/data/daily-tom/task_state.json` — `tasks` (per-ID `first_seen`/`last_seen`/`status`/`group`) and `runs[]` (per-run summary: date, counts, latest_source_section, by_group). The generated `new_section` text is NOT persisted in runs.

## Rollover rules (what carries and what doesn't)
- The sync reads ONLY the latest dated section (between the newest date heading and the next date heading). Lines typed above it (e.g. right under `[Next date]`) or in older sections are invisible to the carry.
- A line counts as a task only under a recognized group header: `[Professional]`, `[Professional - MENA]`, `[Professional - Others]`, `[Personal]`. A `Prefix:` lead (e.g. `MENA:`) maps to the Others/MENA groups. Anything else is silently skipped.
- Hand-typed lines (no `[n:xxxxx]` ID) DO carry: the sync assigns a fresh ID and copies them into the new day. The source line is left untouched (no ID written back). Fresh-ID `first_seen` == rollover date is the fingerprint of "DJ typed this yesterday".
- Done shorthand: leading `✅`, `[x]`, `x `, or bare `x` before an uppercase/digit (`xIT...`) → stamped `✅` in the source section, dropped from rollover.
- In-progress shorthand: leading `>` or `↗️` → stamped `↗️` in source, carried with the marker stripped.

## Parked-task-drop bug (found 2026-07-17)
- Any task line containing a relative park marker `[Nd]` (e.g. `[18d]`) is treated as "park for N days".
- **Bug:** `newly_parked` tasks were counted in the run summary but not written back to the doc — `build_section()` only received carried+returning tasks, and no `batchUpdate` request inserted parked tasks anywhere. With no `[Parking Lot]` section in the doc, parking silently DELETED the task from the doc.
- **Evidence-erasing side effect:** for `↗️` lines, the progress rewrite (`replaceAllText` of the raw line with `↗️ <cleaned text>`) stripped the `[Nd]` marker from the source section, so afterwards there was no visible trace of why the task vanished.
- Concrete case: on the 2026-07-17 rollover, "Development PNL" and "MENA: Equity Plan" disappeared from the new section. Run summary showed `newly_parked_from_latest: 3` (those two + "MENA: Mgmt training programs [18d]", the only one whose marker survived in the source because it had no ↗️ prefix).
- Fix direction: parked tasks should be written into a real `[Deferred]`/`[Parking Lot]` section with `[M/D]` return dates and returned only once.

## Deferred-return duplication/index-shift bug (found 2026-08-17)
- Symptom: latest Daily ToM section ballooned from ~25 tasks to 100+ tasks, with repeated identical `[n:<id>]` lines, cross-section misplacements, corrupt IDs such as `Hermes upgrade [n:8e92essional]`, and bad spacing.
- Root cause: returned deferred lines were deleted after inserting the new day while using their original Google Docs indexes. Because `[Deferred]` sat below `[Next date]`, the insertion shifted those indexes, so deletes hit unrelated content and deferred-return tasks kept reappearing/duplicating into future days.
- Additional hardening added: `build_section()` dedupes by task ID/text before writing a new day, and corrupt visible IDs are normalized back to known IDs from `task_state.json` when the visible text matches.
- If this recurs, immediately pause cron job `Daily ToM sync at 5AM ET`, back up current doc paragraphs, clean only the latest dated section, run `/opt/data/scripts/daily-tom-context.py`, dry-run tomorrow with `/opt/data/google-accounts/.venv/bin/python /opt/data/scripts/daily-tom-sync.py --date YYYY-MM-DD`, verify no duplicate IDs/corrupt IDs, then resume cron.

## Offline audit recipe (read-only, safe under DJ's Google policy)
1. Check the last run: `runs[-1]` in `task_state.json` (counts, source section, by_group). Compare `carried` against what you count in the source section.
2. Check per-task fate: `tasks[<id>].last_seen` — carried tasks get today's date; dropped/parked keep yesterday's.
3. Re-run the parse offline against the live doc:
   - importlib-load `/opt/data/scripts/daily-tom-sync.py`, but register the module in `sys.modules` BEFORE `spec.loader.exec_module()` or the `@dataclass` decorators crash (`sys.modules.get(cls.__module__)` returns None).
   - Fetch the doc with `get_creds('/opt/data/google-accounts/personal')` + Docs API, `extract_paragraphs`, then walk paragraphs between two date headings applying `infer_group` + `clean_task_line` to label each line carried / done / parked / skipped.
   - Run with `/opt/data/google-accounts/.venv/bin/python`.
- Note: after a rollover the source section still contains carried lines (carry = copy, not move), so yesterday's section is auditable post-hoc — except where earlier buggy rewrites erased markers.
