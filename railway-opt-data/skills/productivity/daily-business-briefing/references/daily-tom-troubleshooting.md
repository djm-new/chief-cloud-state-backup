# Daily ToM troubleshooting notes

Use this when the Daily ToM sync/context pipeline alerts, fails a Chief health check, or DJ asks to run the ToM sync manually.

## Components

- Sync script: `/opt/data/scripts/daily-tom-sync.py`
- 5AM ET wrapper: `/opt/data/scripts/daily-tom-daily-5am-et.sh`
- Context extractor: `/opt/data/scripts/daily-tom-context.py`
- Google account wrapper: `/opt/data/scripts/google-account personal ...`
- Health probe: `/opt/data/scripts/chief_operational_health.py`

## Expected health marker

`chief_operational_health.py` expects Daily ToM context output to contain exactly:

```md
## Daily Top of Mind Context
```

If the extractor has fallback/error paths, they should emit the same marker before the error explanation. Otherwise a genuine upstream fetch failure can be misreported as a markdown-format issue.

## Manual run for today's ET date

When DJ asks to "run it for today" and side effects are explicitly intended:

```bash
TODAY="$(TZ=America/New_York date +%F)"
/opt/data/google-accounts/.venv/bin/python /opt/data/scripts/daily-tom-sync.py --date "$TODAY" --apply
/opt/data/scripts/daily-tom-context.py | sed -n '1,80p'
/opt/data/scripts/chief_operational_health.py
```

Report the JSON `status`, `date`, `latest_source_section`, counts, groups, then confirm the context extractor sees the new current section and health is OK.

## Runtime/dependency path check

The Google Workspace scripts may depend on Python Google API packages. If system `python3` lacks those packages, prefer a persistent `/opt/data` runtime instead of installing into transient/system Python:

```bash
uv venv /opt/data/google-accounts/.venv
uv pip install --python /opt/data/google-accounts/.venv/bin/python \
  google-api-python-client google-auth-oauthlib google-auth-httplib2
```

Then ensure wrappers that invoke Google APIs use `/opt/data/google-accounts/.venv/bin/python` with a `python3` fallback. This keeps the integration tied to the persistent Railway volume and avoids code changes under `/opt/hermes`.

## Schedule shape

For the Daily ToM 5AM ET job, avoid hourly cron wakeups. Use UTC candidate hours for DST plus the wrapper's ET/date guard:

```cron
0 9,10 * * *
```

The EDT candidate is 09:00 UTC; the EST candidate is 10:00 UTC. Only the matching 5AM ET candidate should do work; the other should exit silently.

## Google Docs style preservation

When `daily-tom-sync.py` creates a new day, plain `insertText` inherits the paragraph style at the insertion point. Because the insertion point is near `[Next date]`, this can accidentally make every inserted paragraph `HEADING_2`. Preserve the established document pattern explicitly:

- Date line: `HEADING_2`
- Blank lines, section labels (`[Professional]`, etc.), and task rows: `NORMAL_TEXT`

Preferred implementation pattern in `daily-tom-sync.py`:

1. Build `inserted_text = new_section + "\n"`.
2. Add the `insertText` request first.
3. Add one `updateParagraphStyle` request per inserted paragraph over the inserted ranges.
4. Set only `fields: "namedStyleType"` so other doc formatting is not disturbed.

If a generated day already has bad styles, repair just that day's paragraph ranges: keep the date paragraph `HEADING_2`; set all paragraphs until the next date section to `NORMAL_TEXT`. Verify by reading Docs API `paragraph.paragraphStyle.namedStyleType`, not by eyeballing extracted plain text.

## Manual task additions

When DJ explicitly asks to add a ToM item to today's list, it is an approved Docs edit. Add it to the current top dated section, usually under `[Professional]` unless the request clearly names another section. Preserve the ToM task-id convention by appending a fresh `[n:<id>]`, and verify with `/opt/data/scripts/daily-tom-context.py` that the item appears under the expected section.

Be careful with Google Docs insertion indexes: fetch the live doc, find today's date paragraph, find the section paragraph and next section/date boundary, then insert before that section's trailing blank line or before the next section. Do not use stale indexes from a previous read after making edits.

## Keyboard marker normalization

DJ uses fast keyboard shorthands in the Google Doc:

- leading `x`, `x `, `X `, or `[x]` means completed and should be converted to `✅ ` in the source day
- leading `>`, `> `, or `[>]` means in-progress and should be converted to `↗️ ` while the item is active, but the marker should *not* carry into the next day

Important implementation details:

- `daily-tom-sync.py` must treat lowercase no-space `xTask` as completed but avoid treating uppercase task names such as `XM comp` as completed. The conservative regex is `x(?=[A-Z0-9])` for no-space lowercase `x`, plus spaced `[xX]\s+`.
- Completed tasks should be removed from rollover *and* rewritten in-place to `✅ ...` in the source paragraph so the historical day visibly shows completion.
- Preserve visible in-progress markers on the source day, but strip them from the next day's carried-forward section so `>Task` / `↗️ Task` becomes plain `Task` on rollover.
- If existing historical paragraphs have raw markers, batch-rewrite the live Google Doc via Docs API by replacing only the paragraph content prefix; skip date lines, `[Next date]`, `[Parking Lot]`, and `[Section]` headings. Verify there are zero remaining task paragraphs matching raw `x`/`>` prefixes.
- The Daily ToM context extractor should also recognize the same completion shorthand so `xTask` does not leak into briefing context before the next sync/cleanup pass.
- Regression tests should cover both sides of the behavior: source-day rewrite to `✅` and next-day carry-forward without `x`/`↗️` markers.

## Verification checklist

- `bash -n /opt/data/scripts/daily-tom-daily-5am-et.sh`
- `/opt/data/google-accounts/.venv/bin/python -m py_compile /opt/data/scripts/daily-tom-sync.py /opt/data/scripts/daily-tom-context.py`
- `/opt/data/scripts/daily-tom-context.py` starts with `## Daily Top of Mind Context`
- Context says `Current ToM section: <today's date>` after an applied run
- If styles were changed: inspect Docs API paragraph styles for the current day (`HEADING_2` date, `NORMAL_TEXT` body)
- If marker normalization changed: verify no non-structural paragraph begins with raw `[x]`, `x`, `X `, `[>]`, or `>` markers; completed items should show `✅`, in-progress items should show `↗️`.
- `/opt/data/scripts/chief_operational_health.py` ends with `Status: OK`
- `hermes cron list` shows Daily ToM enabled with schedule `0 9,10 * * *`
