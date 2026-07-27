# Google Sheets Selection History for Review Galleries

Use this when DJ wants a durable audit/history of every keep/discard decision across multiple photo sets, beyond the current shared state JSON.

## Pattern

Keep two layers:

1. **Current state** in the app/Railway volume, e.g. `/data/<project>/decisions.json`, keyed by stable manifest item IDs. This drives the live gallery and contact sheet.
2. **Append-only history** in Google Sheets, one row per actual selection change. This survives photo swaps and gives DJ a simple dated catalog.

Do not treat the Sheet as the primary live database for the gallery. Use it as an audit/export log so the app remains fast and resilient if Google is slow.

## Recommended sheet columns

Create a spreadsheet in DJ's personal Gmail Drive when requested, with a `Selections` tab and frozen header row:

- Timestamp ET
- Timestamp UTC
- Reviewer
- Device
- Session ID
- Set ID
- Item ID
- Book/Item Title
- Category
- Decision (`keep`, `discard`, or `clear`)
- Rotation
- Source Photo
- App URL

## Reviewer attribution

If there is no login system, prompt once per device/browser at the first actual selection change:

```js
const REVIEWER_NAME_KEY = "<project>-reviewer-name-v1";
function reviewerName() {
  let name = localStorage.getItem(REVIEWER_NAME_KEY) || "";
  if (!name) {
    name = window.prompt("Who is making this selection?", deviceLabel()) || deviceLabel();
    localStorage.setItem(REVIEWER_NAME_KEY, name.trim() || deviceLabel());
  }
  return localStorage.getItem(REVIEWER_NAME_KEY) || deviceLabel();
}
```

Send `reviewerName`, `deviceLabel`, `sessionId`, `setId`, `itemId`, `title`, `source`, and `appUrl` with the decision PATCH.

## What to log

Append rows only for real selection changes:

- keep
- discard
- clear/undecided

Avoid noisy rows for category-only, rotation-only, heartbeat, gallery reload, shared-state refresh, or migration/backfill updates unless DJ explicitly asks for them.

Use a flag like `logSelection: true` from the client only when `setDecision(...)` is called by a user action. Server-side PATCHes with `logSelection: false` should still update current state but not append to the Sheet.

## Server-side implementation notes

- Add a local JSONL fallback log on the persistent volume, e.g. `/data/<project>/selection-log.jsonl`, before/alongside the Google append. This gives a recovery trail if Sheets append fails.
- Configure the Google Sheet ID and token as Railway variables; do not commit tokens.
- If using OAuth token JSON, store it as base64 in an env var such as `BOOK_SORTER_GOOGLE_TOKEN_JSON_B64` and decode at runtime.
- Use `google-auth` to refresh the token and a direct Sheets API HTTP append to avoid pulling the full Google API client into production unless needed.
- Use ET and UTC timestamps. DJ prefers times in ET for operational views.

Example append endpoint behavior:

```python
saved = current_state_update(...)
sheet_appended = False
logged = False
if bool(record.get("logSelection")):
    entry = selection_log_entry(item_key, record, saved)
    append_jsonl(entry)
    sheet_appended = append_google_sheet_row(entry)
    logged = True
return {"ok": True, "logged": logged, "sheetAppended": sheet_appended}
```

## Verification

- Create/format the Sheet and verify the owner/account is DJ's `@gmail.com` account when requested.
- Run local tests for both logging and non-logging PATCHes.
- Do an end-to-end append verification with a disposable row, then delete that verification row so the sheet stays clean.
- Deploy, verify the live review HTML contains the reviewer/set/logging markers, and verify `/api/selection-log` responds.

## Backfill policy

Do not backfill historical selections with guessed reviewer names. If old records lack reliable `who` metadata, leave the Sheet clean or import them with an explicit reviewer like `Unknown/backfill` only if DJ asks.