# Manual Crop Correction and Batch Reset for Repeat Gallery Runs

Use this when the automatic crop generator produces a mostly-good but imperfect repeat batch (merged items, furniture/background crops, or missed edge items).

## Pattern from Book Sorter second batch

1. Run the existing generator first; do not skip the proven pipeline.
2. Generate a quick contact-sheet image from the produced `sample-crops/manifest.json` and inspect it visually.
3. If the crop set is wrong, manually replace the manifest/crops rather than shipping imperfect detection:
   - Use the original source image.
   - Define explicit boxes `[x, y, w, h]` for each visible item.
   - Write each corrected crop to `sample-crops/<sample>/<NN>.jpg`.
   - Write `sample-crops/manifest.json` with stable IDs (`01-01`, `01-02`, ...), readable titles, source, box, aspect ratio, and rotation.
   - Remove stale crop files whose IDs no longer exist.
4. Generate a second contact sheet and visually verify:
   - one real object per crop;
   - no furniture/floor-only crops;
   - no merged multiple-object crops;
   - no missed obvious items;
   - orientation is readable/upright.
5. Update tests to assert the new manifest count, generation marker, rotation set, and a couple of known titles.
6. Commit/push and deploy the existing Railway service.
7. Verify production manifest/routes/assets first.
8. Only after the new manifest is live, clear current active decisions (`DELETE /api/decisions`) so old decisions keyed by reused stable IDs do not appear on the new batch.
9. Verify `/api/decisions` is empty after reset.

## Why reset after deploy

Stable item IDs are reused across batch swaps (`01-01`, `01-02`, ...). If old `decisions.json` remains after the new manifest goes live, prior keep/discard choices can incorrectly attach to new books. Clear the live active decision state after the new deployment is verified, while preserving append-only Sheet history as the durable archive.

## Minimal manual manifest script shape

```python
from pathlib import Path
import cv2, json

root = Path('/opt/data/projects/book-sorter-mvp')
img = cv2.imread(str(root / 'sample-images/01.jpg'))
outdir = root / 'sample-crops' / '01'
outdir.mkdir(parents=True, exist_ok=True)
for p in outdir.glob('*.jpg'):
    p.unlink()

items_data = [
    ('01-01', 'Readable Title', [x, y, w, h]),
    # ...
]

items = []
for idx, (item_id, title, box) in enumerate(items_data, 1):
    x, y, w, h = box
    crop = img[y:y+h, x:x+w]
    out_name = f'{idx:02d}.jpg'
    cv2.imwrite(str(outdir / out_name), crop, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    items.append({
        'id': item_id,
        'title': title,
        'src': f'/sample-crops/01/{out_name}',
        'source': 'sample-01.jpg',
        'box': [int(x), int(y), int(w), int(h)],
        'fill': 1.0,
        'aspectRatio': round(w / max(1, h), 4),
        'rotation': 0,
    })

(root / 'sample-crops' / 'manifest.json').write_text(
    json.dumps({'generatedBy': 'manual-crop-correction-v1', 'items': items}, indent=2),
    encoding='utf-8',
)
```
