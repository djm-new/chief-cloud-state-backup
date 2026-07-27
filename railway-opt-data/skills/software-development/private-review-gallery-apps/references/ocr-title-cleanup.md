# OCR/title cleanup for review-gallery batches

Use when generated crops have generic labels (`Book 01`, `Item 07`) but the gallery/contact sheet/Google Sheet should be usable as a durable record.

## Pattern

1. Run title extraction on the final cropped item images, not the original wide photo.
2. Use the manifest item id as the join key (`01-01`, `01-02`, etc.). Never join OCR output by title text or image hash.
3. Prefer conservative titles:
   - Keep clear title text and punctuation/capitalization that helps humans identify the item.
   - Remove OCR noise, repeated words, prices, publisher blurbs, and debug labels.
   - If the crop is too blurry/partial, keep a generic title or mark it for manual cleanup rather than hallucinating.
4. Update both:
   - `sample-crops/manifest.json` item `title` fields so the live app/contact sheet use the names.
   - Any durable history/export sheet rows keyed by `Book ID` / item id.
5. Commit, push, deploy, and verify the live manifest rather than only local files.

## Verification

- Fetch the production manifest and check `generatedBy` or another deployment marker plus several known item titles.
- Read the Google Sheet rows with `valueRenderOption=FORMULA` when thumbnails use `=IMAGE(...)` formulas; verify titles changed without breaking thumbnail formulas.
- Run the app's tests after manifest/title changes.
- Spot-check low-confidence multilingual titles manually in the live/contact-sheet view when possible.

## Pitfalls

- Do not leave durable Sheet rows as `Book 01` once the sheet is meant to be the long-term archive.
- Do not overwrite reviewer/date/decision fields while updating titles.
- Do not treat OCR as authoritative for blurry Spanish/children's-book text; best-effort is acceptable, but fabricated titles are worse than generic labels.
- If thumbnails are Drive-backed formulas, preserve the exact `=IMAGE("https://drive.google.com/uc?export=view&id=...",4,120,90)` cell contents while editing adjacent columns.
