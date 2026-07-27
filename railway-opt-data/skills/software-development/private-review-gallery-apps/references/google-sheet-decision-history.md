# Google Sheet Decision History for Review Gallery Apps

Use this when DJ wants review-gallery decisions cataloged outside the app, especially before replacing a photo batch.

## Goal

The app keeps the current shared state, but Google Sheets/Drive becomes the durable history:

- one row per keep/discard/clear selection
- human-readable enough to identify the item later
- small enough not to waste storage on books/items that were tossed

## Recommended visible Sheet columns

Keep the Sheet useful for humans. DJ explicitly pushed back on API-export-style columns; default to a simple review log, not a database dump.

Preferred visible columns, in this order:

1. `Thumbnail`
2. `Title`
3. `Decision`
4. `Reviewer`
5. `Date`
6. `Batch`
7. `Book ID`
8. `Category`
9. `Notes` (optional blank column)

Do not show these unless explicitly requested; keep them only in app JSONL/API internals if needed for debugging:

- UTC timestamp
- device
- session ID
- source photo
- app URL
- archived image URL
- rotation
- debug/provenance fields

Important Google Sheets quirk: item IDs like `01-01` can be auto-coerced into dates/serial numbers under `USER_ENTERED`. When appending or backfilling `Book ID` / `Item ID`, either use `RAW` for that cell or prefix the value with an apostrophe (e.g. `'01-01`) so it remains visible as text.

## Logging semantics

- Append rows for selection changes: `keep`, `discard`, and `clear`.
- Do not append category-only or rotation-only changes unless DJ asks for full audit logging.
- Ask reviewer name once per browser/device; store it in localStorage and send it with future rows.
- Backfill old decisions honestly: if reviewer was not captured, use `Backfill — unknown`; do not infer from device/session data.
- Keep current app state separate from the append-only log.

## Lightweight thumbnails

Do not store full crop images long-term for discarded items. Archive a tiny thumbnail instead:

- resize to max dimension around 320 px
- JPEG quality around 55
- optimize/progressive if available
- typical target: a few KB per item (Book Sorter backfill averaged ~4 KB)

For Google Sheets thumbnails:

- Store image files in a Drive folder, e.g. `Book Sorter Decision Images`.
- Put the durable image URL in a hidden/secondary `Archived Image URL` column.
- Use an `=IMAGE("<url>",4,120,90)` formula for the visible thumbnail column.
- If the image URL must render reliably in Sheets, make the Drive thumbnail file readable by anyone with the link. This is a privacy tradeoff; use tiny item crops, not full room/floor photos.

## App-side implementation outline

Client sends on selection save:

```json
{
  "category": "activity",
  "decision": "keep",
  "rotation": 90,
  "reviewerName": "Sandra",
  "deviceLabel": "iPhone",
  "sessionId": "...",
  "setId": "kids-books-shelf-2026-07-24",
  "itemId": "01-03",
  "title": "Book 03",
  "source": "sample-01.jpg",
  "appUrl": "https://.../books/secret",
  "cropUrl": "https://.../sample-crops/01/03.jpg",
  "logSelection": true
}
```

Server behavior:

1. Save/update current decision state.
2. If `logSelection` is true, create an append-only local JSONL entry as fallback.
3. Fetch `cropUrl`, create a lightweight thumbnail, and upload it to Drive.
4. Append a Sheet row with human fields plus `Archived Image URL` and thumbnail formula.
5. Return `sheetAppended`/`logged` flags for verification.

Use environment variables for production secrets/config:

```text
BOOK_SORTER_GOOGLE_SHEET_ID=<spreadsheet id>
BOOK_SORTER_GOOGLE_IMAGE_FOLDER_ID=<drive folder id>
BOOK_SORTER_GOOGLE_TOKEN_JSON_B64=<base64 encoded OAuth token JSON>
BOOK_SORTER_SET_ID=<current batch id>
```

## Verification

- Check the Sheet row count and headers via Sheets API.
- Fetch values with `valueRenderOption=FORMULA` to verify `=IMAGE(...)` formulas, because formatted values may omit formula text.
- Query the Drive folder and confirm active file count plus total size.
- Backfill should be idempotent: use a recognizable session ID like `backfill-current-content` and skip if rows already exist.
