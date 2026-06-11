# Daily ToM / Top of Mind routing notes

Use this when a Telegram or thought-capture message contains an explicit instruction like `add to TOM: ...` or `add to top of mind ...`.

## Canonical action

- Use `daily-tom-add.py --apply` to update the Google Doc.
- Treat explicit “add to Top of Mind / ToM” instructions as a **doc-sync request**, not just a local scratchpad note.
- Do **not** treat this as only a session todo / memory note.
- If the user gives a direct instruction inside a thought-capture message, log the thought **and** apply the ToM change.
- If Google auth or the doc write path is unavailable, say so plainly and do not imply the item was synced.

## Routing policy

Default routing is model-assisted, with explicit prefix overrides first and a deterministic fallback second.

1. If the item is explicitly prefixed, honor it:
   - `Personal: ...`
   - `MENA: ...`
   - `Other:` / `Others:`
2. Otherwise, use the lightweight router model (`gpt-5.4-mini`) to choose one of:
   - `Personal`
   - `Professional - MENA`
   - `Professional - Others`
   - `Professional`
3. If the model is unavailable, fall back to conservative heuristics.

Useful Personal cues for the fallback include:

- ticket(s)
- flight(s)
- hotel(s)
- travel
- trip
- `book ... ticket/flight/hotel/travel/trip`

Append new items to the **bottom** of the target group by default.

Normalize entries to proper capitalization before writing them.

Priority / starred items (`*` or `!`) still go to the top.

If the user explicitly prefixes the item, honor it:

- `Personal: ...`
- `MENA: ...`
- `Other:` / `Others:`

## Ordering

- Append new items to the **bottom** of the target group by default.
- Only priority / starred items go to the top.
- If the user starts the item with `*` or `!`, treat it as priority and insert it at the top of the group.
- Strip the priority marker before writing the final stored text.

## Corrections and moves

- If an item was placed in the wrong group, remove the mistaken doc entry first, then re-add it with the correct group.
- After a move, verify the live Google Doc rather than trusting the helper's `already_present` response alone.

## Pitfalls

- Do not confuse the session todo list with the actual Daily ToM Google Doc.
- Google Docs updates may lag briefly; if the helper says `already_present` after a recent delete/re-add, verify the live doc text before assuming the change failed.
- When the user says "add to TOM" in plain language, prefer the Google Doc update over any local scratchpad.
