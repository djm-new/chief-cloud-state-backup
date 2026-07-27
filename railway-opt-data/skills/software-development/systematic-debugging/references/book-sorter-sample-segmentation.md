# Image gallery crop/segmentation pitfall

## Symptom
A gallery app shows many duplicated or badly cropped tiles after loading bundled sample images. Cards may represent the whole floor photo, repeated layouts, or incorrect crops.

## Root cause pattern
The sample/demo path is often treated as a special case and routed through hardcoded crop boxes or a layout that only matched an earlier example image set. This can silently survive UI updates because the page still renders "successfully".

A second failure mode is the opposite: removing the stale hardcoded branch and forcing all bundled images through a weak heuristic detector can collapse each floor photo into one large component. The count then becomes the number of source photos, not the number of books.

## Debugging checklist
1. Inspect the deployed client code, not just the server response.
2. Confirm whether sample/demo assets are being sent through a hardcoded branch.
3. Compare the sample path with the upload path:
   - If the sample images are ordinary unknown inputs, use the same detector path as uploads.
   - If the sample images are bundled/calibrated fixtures for a private review app, hand-labeled per-image crop specs are acceptable and often better than a brittle color/edge detector.
4. Build a contact sheet of the **actual generated crops after applying the same rotations/transforms the app uses** and inspect it before declaring victory. It exposes issues that counts do not: sideways/upside-down covers, mostly-floor/wood tiles, crops that include multiple books, and crops that only include a sliver of a book.
5. Hold the review to the product requirement, not to “better than before”: every tile should contain exactly one item/book, no wood/floor-only tiles, and cover text should be readable upright left-to-right. Do not say “fixed” until the generated contact sheets or live UI satisfy that bar.
6. Remove invalid crops rather than keeping a wrong card with a nice label. A partial/wood/multi-book crop is worse than one missing candidate in a human review workflow.
7. Be skeptical of automated OCR/orientation scores: use them as hints only. Book-cover art, rotated titles, and decorations can make OCR prefer the wrong orientation. Final validation must be visual inspection of the produced crops/live webpage.
8. If users can manually rotate/correct cards, make that correction data exportable or visible to the operator. Browser `localStorage` is invisible from the server/agent; without an export/share endpoint, you cannot learn from the user's manual fixes. Add a "copy corrections" or diagnostics export containing counts and per-item rotations before asking the user to review many tiles.
9. When replacing hardcoded crop specs with generated static crops, preserve the calibrated metadata separately: titles, default rotations, invalid-crop removals, and any source-to-card mapping. A better crop algorithm can still regress UX badly if every manifest item becomes `Photo N book NN` with `rotation: 0`.
10. Treat review modal copy as user-facing, not debug output. Use the deciphered title when available; if it cannot be deciphered, show `Untitled`. Do not show hashes, rotation degrees, or raw generated IDs in the detail header/subtitle. Prefer concise labels such as `Category: Activity`.
11. Match detail-modal actions to gallery actions. If the gallery uses over-image green check/red X controls, put the same controls on top of the modal image; keep rotation controls out of the gallery tiles unless explicitly requested. After a modal decision is made, render the same large keep/discard overlay on the blown-up image immediately so the user does not have to return to the gallery to confirm state. The modal overlay itself should be tappable to clear the decision, and pressing the same decision button again should toggle that decision off.
12. Detail review should support continuous browsing. Add left/right keyboard navigation and mobile swipe navigation in the blown-up modal so reviewers can move to the next/previous card without closing back to the gallery. For touch, bind `touchstart`/`touchend` to the image wrapper, ignore button targets, require a horizontal threshold, and ignore mostly vertical swipes. Add visible mobile affordances (for example side chevrons plus “Swipe left/right”) because swipe support is otherwise undiscoverable.
13. For circular over-image controls, prevent flex/grid stretching: set equal width/height, min-width/min-height, `aspect-ratio: 1 / 1`, `flex: 0 0 <size>`, and `border-radius: 50%`. A `999px` radius alone can become an oval when the row stretches the buttons. If the user changes their mind on transparent buttons, keep the circular sizing rules and only swap the fill/border colors.
14. For collaborative review apps, localStorage alone is insufficient. If two people/devices need to stay in sync, add server-side shared state for decisions/categories/rotations, load it before building cards, save immediately on every decision/category/rotation mutation, and periodically refresh it while the app is open. Keep localStorage as a fallback cache, not the source of truth.
15. If the user wants to know who is using a private review app, add lightweight activity tracking: generate a per-browser session ID, send a heartbeat on load and while visible, count actions (keep/discard/clear/category/rotation), record first/last seen, active seconds, page loads, rough device label, and expose a secret admin activity page. Do not overclaim identity unless the app asks the reviewer to self-identify or uses separate per-person links.
16. When a non-technical reviewer may not understand a secret-link tool, add an onboarding/interstitial explanation before the gallery. Use the user-requested wording closely, name the intended reviewer if requested, and provide one obvious “start reviewing” action.
17. Detail modal decision overlays need to be visibly larger than gallery overlays because the image is the focus state. Use a modal-specific class (for example `font-size: clamp(7rem, 32vw, 14rem)`) rather than relying on the gallery overlay size.
18. Distinguish static crop loading from re-detection. On reload, a bundled static review app should fetch the generated manifest/crop files, construct cards, then reapply saved state; it should not rerun image segmentation unless the user uploads new photos or explicitly regenerates. If reload feels slow, consider precomputing more metadata, reducing per-image canvas hashing, or caching the manifest-derived groups.
19. Verify that generated item IDs/hashes still match downstream assumptions. Example: if duplicate matching uses `BigInt('0x' + hash)`, hashes must remain valid hex strings; do not prefix them with filenames.
20. Verify the fix on the live route after redeploying, and if possible inspect the live UI itself, not only the served HTML markers.

## Regression tests for static gallery apps
- Add a test that the deployed/static HTML contains per-image fixture keys for every bundled sample image.
- Add a count guard: total crop specs should exceed the number of source photos and roughly match the visible item count.
- Add a branch guard: sample labels route through the intended fixture/detector path, and old single-demo constants are absent.
- Add explicit negative guards for known invalid crops (for example labels or coordinate boxes that produced mostly floor/wood).
- If you add default rotations, test for representative rotated spec/manifest entries so future edits do not silently reset everything to `rotation: 0`.
- If generated crops replace hand specs, test that manifest items preserve user-facing titles, reject known invalid crop IDs, and use an explicit generated-by version reflecting title/rotation overrides.
- For mobile/gallery controls, test both markup and CSS markers: over-image detail controls exist, gallery rotate controls are absent when not wanted, and circular buttons include fixed dimensions plus `aspect-ratio: 1 / 1` / `border-radius: 50%`.
- For detail modals, test that headers/subtitles do not expose debug strings like raw hashes, crop IDs, or `rotate 0°`; user-facing text should be title/`Untitled` plus concise category.
- For blown-up modal review, test that swipe navigation markers exist (`touchstart`, `touchend`, `navigateModal`), that a visible swipe affordance exists (chevrons or copy such as “Swipe left/right”), that modal decisions render an over-image keep/discard overlay, and that repeated taps / overlay taps can clear the decision.
- For collaborative review apps, test server-side shared decision endpoints and client markers: load shared decisions before card creation, save on every mutation, clear shared state when “clear” is clicked, and periodically refresh shared state for cross-device sync.
- For activity tracking on private review apps, test server endpoints (`/api/activity`, heartbeat, action logging), client markers for session ID + heartbeat/action fetches, and the secret admin activity page. Verify production with a harmless probe heartbeat/action and then read the activity API/admin page.
- For onboarding/interstitial pages, test that the requested reviewer-facing copy and dismiss/start action are present, and that dismissing only hides the overlay rather than blocking gallery loading or shared-state sync.
- For detail-modal decision UX, test that pressing the same keep/discard control routes through toggle logic, that modal overlays use a larger modal-specific size, and that swipe affordances are visible in the markup (`Swipe left/right`, left/right chevrons).
- For static generated crop apps, test reload semantics indirectly: the page should fetch the generated crop manifest and apply saved browser state rather than rerunning segmentation or reverting titles/rotations on each page load.

## Contact-sheet verification pattern
When crop specs live in a static HTML/JS file, generate thumbnails from the same coordinates **and the same default rotations** and inspect them as a grid before deploy. Number each tile so feedback maps back to a spec. Example shell pattern:

```bash
rm -rf /tmp/book-crops && mkdir -p /tmp/book-crops
python3 - <<'PY'
import re, subprocess
from pathlib import Path
html = Path('books_sorter.html').read_text()
rot_filter = {0: '', 90: ',transpose=1', 180: ',transpose=1,transpose=1', 270: ',transpose=2'}
for sample in range(1, 6):
    key = f'"sample-{sample:02d}.jpg"'
    start = html.index(key)
    arr_start = html.index('[', start)
    arr_end = html.index('],', arr_start)
    block = html[arr_start:arr_end]
    specs = re.findall(r'\{ title: "([^"]+)", x: (\d+), y: (\d+), w: (\d+), h: (\d+), rotation: (-?\d+), pad: (\d+) \}', block)
    for idx, (_, x, y, w, h, rot, pad) in enumerate(specs, 1):
        x, y, w, h, rot, pad = map(int, (x, y, w, h, rot, pad))
        cx, cy = max(0, x - pad), max(0, y - pad)
        cw, ch = min(960 - cx, w + pad * 2), min(1280 - cy, h + pad * 2)
        vf = (
            f'crop={cw}:{ch}:{cx}:{cy}{rot_filter[rot % 360]},'
            'scale=180:180:force_original_aspect_ratio=decrease,'
            'pad=220:220:(ow-iw)/2:(oh-ih)/2:black,'
            f'drawtext=text={idx}:x=8:y=8:fontsize=28:fontcolor=yellow:box=1:boxcolor=black@0.7'
        )
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error', '-i', f'sample-images/{sample:02d}.jpg',
            '-vf', vf,
            f'/tmp/book-crops/s{sample}_{idx:02d}.jpg'
        ], check=True)
PY
for s in 1 2 3 4 5; do
  ffmpeg -y -loglevel error -framerate 1 -i "/tmp/book-crops/s${s}_%02d.jpg" -frames:v 1 -vf "tile=5x4" "/tmp/book-crops/sheet${s}.jpg"
done
```

Then inspect each `sheet*.jpg` (with vision or manually) and patch rotations/removals before redeploying.

## Verification
- Load the live gallery and confirm the card count roughly matches visible books.
- Check that cropped thumbnails are individual books, not the whole floor shot.
- Probe the live HTML for unique markers (`SAMPLE_BOOK_SPECS_BY_FILE`, expected spec count, intended branch) instead of only checking `/health`.
- If a heuristic detector still mis-crops, either tune thresholds with evidence or switch the bundled fixtures to explicit per-image crops; do not guess by toggling between broad architectural approaches.