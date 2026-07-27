---
name: private-review-gallery-apps
description: Use when building private mobile-first review/sorting gallery apps for household items, books, clothing, photos, inventory cleanup, or similar keep/discard workflows. Covers crop/contact-sheet generation, shared server-side decisions, activity tracking, Railway deployment, and UX patterns DJ already approved.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [gallery, review-app, keep-discard, railway, mobile, activity-tracking]
    related_skills: [railway-app-deployment, github-pr-workflow, systematic-debugging]
---

# Private Review Gallery Apps

## Overview

Use this skill to avoid relearning the workflow from the Book Sorter project when DJ wants another simple private review app, such as clothing to keep/donate, books to read, toys to discard, artwork to archive, or any photo-based selection workflow.

The proven pattern is:

1. Take one or more wide/floor/table photos of many objects.
2. Generate one crop per item, best-effort automatically.
3. Present a mobile-first gallery with simple keep/discard decisions.
4. Store decisions server-side so multiple people see the same state.
5. Provide a final contact sheet split by decision so DJ can execute the physical task quickly.
6. Deploy as a separate GitHub repo and separate Railway service, with a secret link.
7. When DJ wants durable historical decisions, append each selection change to a Google Sheet with date, reviewer, set, item, category, and decision, while keeping the Railway JSON state as the live current state.

This is not a generic polished SaaS. Optimize for a fast, private, family workflow: clear instructions, big mobile controls, easy shared state, and final output that helps with the real-world sorting job.

## When to Use

Use when the user asks for:

- A gallery app to decide what to keep/discard/donate/toss/read/archive.
- A private link for another person to review items from photos.
- A crop/contact-sheet workflow from floor/table photos.
- Multi-device shared decisions between DJ and another person.
- Activity tracking: whether someone opened the app, last active time, approximate time spent, and actions.
- A final keep/discard contact sheet for physically sorting items.

Do not use for:

- A full inventory-management system with accounts, permissions, search, and long-term cataloging.
- Public marketplace/photo gallery apps.
- Tasks where original high-res photo preservation is the primary requirement.

## Approved Product Pattern

### Reuse-first rule for repeat gallery apps

When DJ asks for another instance of a workflow that already exists (for example, a new books photo after a working book/coloring-book sorter exists), do **not** start by creating new infrastructure. First inspect the existing working repo, Railway service, route map, crop generator, and manifest layout. For a same-class repeat, the default plan is: add/replace the new source photo, rerun the proven crop/manifest pipeline, commit/push, deploy through the existing known Railway path, and verify the real route plus crop assets.

## Approved Product Pattern

### Reuse-first rule for repeat gallery jobs

When DJ asks for another pass of the same review-gallery workflow and an existing app/pipeline already works, **do not start by creating a new repo/service**. First check whether the task is just a new asset/photo set for the current app.

Default repeat-task sequence:

1. Locate the existing working repo and live Railway service.
2. Confirm the current live secret route and manifest/assets.
3. Put the new photo(s) into the existing input location.
4. Rerun the proven crop/manifest generator.
5. Inspect the generated contact sheet/crops visually. If the automatic pass includes furniture/floor-only crops, merges several items, or misses obvious edge items, create a corrected manual manifest and crop set from explicit boxes before deploy; do not ship a known-bad crop set.
6. Commit/push to GitHub.
7. Deploy the existing Railway service if auto-deploy does not fire.
8. Verify the real review route, contact sheet, manifest count, rotations, and at least one live crop asset.
9. If stable item IDs are reused for a new active batch, clear live current decisions only after the new manifest is verified live, so old keep/discard choices do not attach to new items. Preserve append-only Sheet history; reset only the active Railway decision state.

Only create a new repo/service when DJ explicitly wants a separate project or the product boundary truly differs. A new photo for the same family sorting app is usually a pipeline rerun, not infrastructure work.

### Project boundaries

DJ strongly prefers standalone projects to stay separate, but repeat work on an already-working sorter should reuse the existing app/pipeline first:

- If DJ sends a new photo for the same class of review app, start by locating the existing working repo/service and rerunning the established crop/manifest pipeline.
- Create a dedicated GitHub repo/service only when this is truly a new standalone project or DJ explicitly asks for separation.
- Do not place the app inside HealthOS or another unrelated product.
- Verify the real secret route, not just `/health`.
- Use GitHub as source of truth; Railway is deployment/runtime only.

### Access pattern

Use a secret route rather than public navigation:

- Main app: `/items/<secret>` or domain-specific path, e.g. `/books/4f8b2d7c`.
- Admin/activity page: `/admin/activity/<secret>`.
- Contact sheet: `/items/contact-sheet/<secret>`.
- `robots.txt`: disallow all.

### Data persistence

Use server-side saving for shared review state:

- Decisions must not be localStorage-only; DJ and spouse need to see the same state.
- Use a simple JSON file on a Railway persistent volume for MVP speed.
- Mount volume at `/data` and store under `/data/<project-name>/`.
- Keep browser `localStorage` as a fallback/cache only.

Suggested files:

```text
/data/<project>/decisions.json
/data/<project>/activity.json
/data/<project>/selection-log.jsonl  # optional append-only fallback/audit log
```

Decision record shape:

```json
{
  "category": "activity",
  "decision": "keep",
  "rotation": 90,
  "updatedAt": "..."
}
```

### Durable decision history

For repeatable family review workflows, the current in-app state is not enough. Add an append-only history sink before swapping to a new photo set.

Recommended pattern:

- Keep Railway/volume decisions as the **current working state** only.
- Append every keep/discard/clear selection to a Google Sheet in DJ's personal Gmail Drive when requested.
- Capture: timestamp ET, reviewer, batch/set id, item id, category, decision, and a lightweight thumbnail.
- Ask the reviewer name once per browser/device and store it in `localStorage`; send it with each logged selection.
- Do not append noisy rows for category/rotation-only changes unless DJ explicitly asks for full audit logging.
- For backfills where reviewer identity was not captured, label rows honestly as `Backfill — unknown` rather than guessing.
- Treat app crop assets as temporary once the Google archive has a durable thumbnail.

Use lightweight thumbnails for the archive: resize crops to roughly 320px max dimension and JPEG quality ~55. Avoid storing full-size crops/photos for tossed items. The Book Sorter backfill averaged about 4 KB per item after thumbnailing.

For details and Sheet column guidance, see `references/google-sheet-decision-history.md`.

## UI/UX Defaults DJ Approved

For multi-batch review apps, the current `decisions.json` is not enough: it represents only the active set and stable item IDs can be reused after a photo swap. If DJ asks to preserve history, add an append-only Google Sheet log in his personal Gmail Drive. Prompt once per browser/device for the reviewer name at the first real selection change, then append one row for each keep/discard/clear. Keep the Sheet human-readable: visible columns should be `Thumbnail`, `Title`, `Decision`, `Reviewer`, `Date`, `Batch`, `Book ID`, `Category`, and optional `Notes`. Keep debug/provenance details (UTC, device/session, source photo, app URL, archived URL, rotation) out of the visible Sheet unless requested. Do not log category-only, rotation-only, refresh, or migration updates unless explicitly requested. Keep a local JSONL fallback in the Railway volume. See `references/google-sheets-selection-history.md` and `references/google-sheet-decision-history.md` for implementation and verification patterns.

## UI/UX Defaults DJ Approved

### Gallery view

- Mobile-first grid, roughly 3-column on phones where feasible.
- Each card contains exactly one item crop; avoid floor/table-only crops.
- Gallery cards should be uniform size across the grid. Pick the shared card shape from the batch (square for near-square items, portrait/landscape rectangle for the dominant orientation), then render all crops with `object-fit: contain` inside that same card aspect ratio rather than assigning per-item card sizes.
- When using uniform cards with `object-fit: contain`, keep the image/card backing light or transparent. Do not put a dark/black background behind contained crops: repeated exposed backing can look like identical triangular artifacts stamped across multiple photos. If the user reports identical artifacts across several cards, inspect the rendered page/CSS as well as raw crop JPEGs before assuming the crop generator is wrong.
- For undecided cards only, show green check and red X action buttons in the lower corners/over image.
- Once a keep/discard decision exists, hide the corner action buttons on that gallery card; require opening the detail view to change or clear an existing choice. This prevents accidental changes while scrolling.
- Green check and red X controls should look like the same icon family. Prefer inline SVG icons with matching stroke width, rounded line caps, and rounded joins instead of mixed text glyphs (`✓` vs `✕`) that render with different weight/corners.
- Tapping center opens blown-up detail view.
- Decision states:
  - blank = undecided
  - green check overlay = keep
  - red X overlay = discard
- Tapping the same check/X again toggles the decision off in contexts where the controls are intentionally visible (especially the detail view).
- Duplicates should share a decision when duplicate matching is available.

### Detail view

- Title should be the item title if decipherable; otherwise `Untitled`.
- Subtitle should be clean, e.g. `Category: Activity`, not debug text/hash/rotation.
- Green check and red X should appear over the image, matching gallery controls.
- Tapping the large center overlay check/X clears the decision.
- Support swipe left/right to move between items without returning to gallery.
- Make swipe affordance obvious: chevrons and visible `Swipe left/right` hint.
- Manual rotation controls belong in detail view, not on top of every gallery image.
- Covers/items should default to readable/upright orientation as much as possible.

### Intro page/banner

For spouse/family-facing links, add a friendly banner or splash screen explaining what the tool is before showing the gallery. The Book Sorter used:

```text
Hello Sandra!
Let me explain to you exactly what this is. Because you have a respectful and loving husband, instead of someone who would observe four of the same book and just make decisions on his own, this tool was created for you to browse through a selection of items and allow you to decide what we should keep and what we should not.
```

Adjust name/copy to the project, but keep it human and clear.

## Crop Generation Pattern

### For floor/table photos

The most successful Book Sorter approach was not whole-photo review. It generated static crop assets first:

```text
sample-crops/
  manifest.json
  01/01.jpg
  01/02.jpg
  ...
```

Manifest item shape:

```json
{
  "id": "01-02",
  "title": "My First Sticker by Numbers",
  "src": "/sample-crops/01/02.jpg",
  "source": "sample-01.jpg",
  "box": [x, y, w, h],
  "fill": 0.42,
  "aspectRatio": 1.2,
  "rotation": 90
}
```

For books on a wood floor, a useful segmentation method was:

1. Convert source photo to HSV.
2. Estimate floor hue (brown floor) and build a floor mask.
3. Invert to object/book mask.
4. Apply morphology to connect cover regions.
5. Find connected components.
6. Split merged blobs with valley cuts where needed.
7. Tighten boxes to mask pixels.
8. Reject low-fill or floor-like crops.
9. Save crop JPEGs and a manifest.
11. Manually review contact sheets to remove false crops and set rotations/titles.
12. Run a best-effort OCR/title pass over the cropped item images before writing historical Sheet rows. Generic labels like `Book 01` are not useful once the Sheet is the durable record. If OCR confidence is poor, keep the generic label rather than hallucinating; consider a Notes/manual correction column for later cleanup.

For clothing, adapt the segmentation target:

- Use background/floor/table segmentation if items are on a consistent surface.
- If clothing overlaps heavily, use manual bounding boxes or a vision-assisted pass rather than pretending the automatic detector is perfect.
- Generate contact sheets early and inspect actual crops before claiming success.

### Decision keys, batch isolation, and hash matching

Use stable manifest item IDs (`01-01`, `01-02`, etc.) as the canonical server-side decision keys. Do **not** use browser-computed perceptual hashes as the primary key for shared decisions: client-side image decoding/scaling can vary across devices, causing Sandra's phone to save decisions that DJ's browser cannot match even though the server data exists.

For repeat photo swaps where item IDs are reused, isolate all client-side cached state by batch/set id. A flat localStorage key like `hermes-book-sorter-decisions-v1` will leak prior decisions onto a new batch with the same `01-XX` IDs. Prefer:

```js
const CURRENT_SET_ID = "kids-books-batch-3-YYYY-MM-DD";
const STORAGE_KEY = `hermes-book-sorter-decisions-v1:${CURRENT_SET_ID}`;
```

When shared server decisions are available, treat them as authoritative on load. Do **not** merge an empty server response into old local storage; replace local state with server state so a cleared live batch is truly blank:

```js
// Good: server is authoritative for the active batch
state.storage = { ...data.decisions };

// Bad: stale browser decisions survive if server is empty
state.storage = { ...state.storage, ...data.decisions };
```

Recommended record shape:

```json
{
  "01-02": {
    "itemId": "01-02",
    "hash": "...",
    "decision": "keep",
    "rotation": 90,
    "updatedAt": "..."
  }
}
```

Use perceptual hashes only as optional metadata for duplicate grouping or legacy migration. If fixing an older hash-keyed app, keep a temporary fallback lookup like `decisions[item.id] || decisions[legacyHash]`, migrate existing records to stable IDs, and verify `/api/decisions` contains item IDs before reporting completion.

See `references/stable-decision-keys.md` for the migration and verification pattern. See `references/repeat-batch-state-isolation.md` for the repeat-batch stale-decision bug and verification checklist.

## Backend Pattern

A FastAPI MVP is sufficient.

Core routes:

```python
@app.get("/items/<secret>")
def review_page(): ...

@app.get("/items/contact-sheet/<secret>")
def contact_sheet_page(): ...

@app.get("/api/decisions")
def get_decisions(): ...

@app.patch("/api/decisions/{item_key}")
def update_decision(item_key: str, record: dict): ...

@app.delete("/api/decisions")
def clear_decisions(): ...

@app.post("/api/activity/heartbeat")
def heartbeat(payload: dict): ...

@app.post("/api/activity/action")
def action(payload: dict): ...

@app.get("/admin/activity/<secret>")
def activity_admin_page(): ...
```

Use atomic JSON writes:

```python
with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=DATA_DIR, delete=False) as tmp:
    tmp.write(json.dumps(data, indent=2, sort_keys=True))
    tmp.write("\n")
    tmp_path = Path(tmp.name)
tmp_path.replace(target_path)
```

Use a `threading.Lock()` around each JSON store.

## Activity Tracking Pattern

For private family workflows, simple built-in activity tracking is enough.

Client behavior:

- Create/reuse a browser session ID in localStorage.
- Send heartbeat on page load.
- Send heartbeat every 15 seconds while visible.
- Send heartbeat on `visibilitychange`.
- Send action event on keep/discard/clear/category/rotation.

Track:

- `firstSeen`
- `lastSeen`
- `pageLoads`
- `activeSeconds`
- `deviceLabel`
- `userAgent`
- action counts: keep/discard/clear/category/rotation
- `lastAction`

Admin page should show:

- active now (last seen within ~45 seconds)
- last seen
- approximate active time
- page loads
- action counts
- rough device/browser info

## Final Contact Sheet Pattern

After review is complete, create a contact sheet page so DJ can do the real-world task.

Route example:

```text
/items/contact-sheet/<secret>
```

Output:

- Sticky header with counts.
- Filter buttons: All / Keep / Discard.
- Keep section first, discard section second.
- Responsive grid.
- Each card shows image, decision badge, title, category.
- Apply saved rotation.
- Include print CSS so the page can be printed if needed.

For the book-sorting family workflow, the contact sheet was also wired as a dedicated quick-scan page so it could be used directly while physically putting books away.

For the books-specific bootstrap notes and route renaming pattern, see `references/books-review-bootstrap.md`.
For repeat/new-photo updates to an existing sorter app, use `references/book-sorter-photo-swap.md` before considering new infrastructure.
For repeat runs where DJ provides a new photo for an already-working gallery app, see `references/repeat-photo-rerun.md`.
For repeat batches where auto-cropping produces furniture/merged/missing items and stable IDs are reused, see `references/manual-crop-correction-and-batch-reset.md`.
For stable decision-key migration and cross-device sync bugs, see `references/stable-decision-keys.md`.
For append-only Google Sheets history of every selection by date/reviewer/set/item, see `references/google-sheets-selection-history.md`.
For OCR/title cleanup before durable exports or final contact sheets, see `references/ocr-title-cleanup.md`.

## Verification Checklist

Before reporting completion:

- [ ] App is in its own GitHub repo and own Railway service.
- [ ] Secret review route returns 200 and contains expected UI marker.
- [ ] At least one crop asset route returns 200/image content.
- [ ] Gallery loads all manifest items.
- [ ] Check/X buttons are circular and solid unless DJ says otherwise.
- [ ] Detail modal can swipe left/right and visibly indicates swipe support.
- [ ] Same decision toggles off on second tap.
- [ ] Center overlay check/X clears decision.
- [ ] Server-side decisions save and reload across API calls.
- [ ] Decision keys in `/api/decisions` are stable manifest item IDs, not only browser-computed hashes.
- [ ] Cross-page decision lookup works in both gallery and contact sheet using the same stable keys.
- [ ] Railway volume exists and is READY for persistence.
- [ ] Activity API writes and admin page loads.
- [ ] If historical logging is enabled, the Google Sheet exists in the requested account, live selection PATCHes append only real keep/discard/clear rows, the local JSONL fallback responds, and a disposable append test row was cleaned up.
- [ ] Before swapping to the next batch, verify the completed batch has been logged in the durable Sheet/history sink and count rows by `setId`/batch; then clear only the active server decisions after the new batch deploy is verified.
- [ ] If the Sheet/contact sheet is a durable archive, generic labels have been replaced with conservative OCR/manual titles where possible, joined by stable item id, without overwriting decisions/reviewer/date fields.
- [ ] For repeat batches that reuse item IDs, localStorage/cache keys include the current set id and server decisions replace local state on load, so stale local decisions cannot mark a fresh batch.
- [ ] Contact sheet route loads keep/discard from server decisions.
- [ ] Counts in contact sheet match `/api/decisions`.
- [ ] Git status is clean after commit/push/deploy.

## Common Pitfalls

1. **Inventing new infrastructure for a repeat photo/job.** If the working sorter already exists and DJ is asking for another batch/photo, the task is usually to feed the new photo through the existing crop/manifest/app/deploy pipeline. Creating a fresh repo/service first is overcomplication and violates the reuse-first expectation.

2. **Treating solvable GitHub/Railway issues as user blockers.** If credentials/access exist, repo visibility, Railway service connection, deploy triggers, domains, and pipeline reruns are agent-owned problems. Diagnose and fix them silently; only ask DJ when a browser approval, account permission, billing/quota issue, or product decision is genuinely outside agent control.

1. **Rebuilding instead of swapping the photo.** For repeat book/gallery sorters, do not start with a new repo/service. Reuse the existing working app, replace the source photo, rerun the crop/manifest generator, inspect the crop sheet, deploy, and verify the live manifest/route.

2. **Calling GitHub/Railway a blocker without proving the layer.** If access exists, solve GitHub/Railway/repo connection/deploy/pipeline issues autonomously. Only surface a blocker when external user action is genuinely required. Name the layer precisely: GitHub auth, Railway auth, repo trigger, deployment, app route/assets, or crop pipeline.

3. **LocalStorage-only decisions.** This fails multi-person review. Server-side persistence is mandatory for shared workflows.

4. **Hash-keyed shared decisions.** Browser-computed image hashes are not durable primary keys across phones/browsers. Use manifest item IDs as canonical keys, keep hashes only as metadata/fallback, and verify server records plus contact-sheet counts after any migration.

4a. **Flat localStorage across repeat batches.** Reusing a route and stable IDs (`01-01`, `01-02`) for a new photo means stale browser decisions can reappear even after the server is cleared. Namespace localStorage by `CURRENT_SET_ID` and replace local state with server decisions on load; do not merge an empty server response into old browser state.

4b. **Malformed overlay SVGs look like black triangles.** Large decision overlays need explicit SVG path styling (`stroke: currentColor`, rounded caps/joins, `fill: none`). Without it, discard X paths can render as filled black polygons, especially when stale decisions are present.

5. **Deploying under the wrong product.** Do not put a standalone family review app inside HealthOS or another unrelated repo/service. But if DJ is asking for another instance of an existing sorter, do not create new product boundaries unless he explicitly wants a new standalone app.

6. **Claiming crops are good without looking.** Always generate and inspect contact sheets or actual produced crops. DJ cares about visual correctness.

7. **Misdiagnosing repeated visual artifacts as crop errors.** If the same-sized dark triangle/shape appears on several gallery cards, first compare raw crop JPEGs with the rendered app. Uniform cards plus `object-fit: contain` and dark image/card backgrounds can create repeated apparent artifacts that are purely CSS. Fix the backing/background and verify the live HTML/CSS, not only the manifest.

8. **Forgetting orientation.** Automatic segmentation and orientation are separate. Preserve or manually set per-item rotation metadata.

8. **Debug labels leaking into UX.** Users should see titles/categories, not hashes, rotation degrees, or `photo book 13` labels.

9. **No final execution view.** The review gallery is for deciding; the contact sheet is for physically putting away/tossing items. Build both.

10. **Activity tracking without persistence.** Store activity server-side in the same persistent volume as decisions.

11. **Health-only verification.** Always verify the real secret route and specific HTML markers after Railway deploy.
