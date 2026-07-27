# Photographed Item Crop + Review QA

Use this for apps that turn one or more wide photos of physical items on a floor/table into a review gallery (books, documents, products, toys, etc.).

## Product assumptions that worked well

- Treat automatic detection as best-effort and make manual review first-class.
- The reviewed unit should be one isolated item per tile/crop.
- Decisions should be visible at gallery level: green check = keep/approve, red X = discard/reject, blank = undecided.
- Duplicates should normally share one decision unless the user explicitly asks for per-copy decisions.
- If orientation matters, include manual per-item rotation controls that persist in local state and export rotation values.

## Cropping pipeline for floor/table photos

For warm wood-floor book photos, a robust baseline is background-color segmentation rather than hand-authored boxes:

1. Downscale/standardize the source image for deterministic processing.
2. Convert to HSV.
3. Segment the known background/floor hue range.
4. Invert to get foreground/item mask.
5. Clean the mask with morphological open/close.
6. Use connected components to find candidate item blobs.
7. Reject tiny candidates and low-fill boxes so floor-only tiles do not survive.
8. Recursively split merged blobs along low-mask-density vertical/horizontal valleys.
9. Tighten final boxes to foreground-mask pixels before writing crops.
10. Generate a manifest with `src`, `source`, `fill`, `aspectRatio`, `title/category`, and `rotation`.

The important durable lesson is not the exact HSV bounds; tune those to the photo set. The durable workflow is: detect background, invert, clean, split merged components, apply fill guards, and verify contact sheets before claiming quality.

## QA gates before saying it is fixed

- Build a contact sheet or otherwise inspect the actual produced crops.
- Reject any tile that is wood/table/floor only.
- Reject or split any tile containing multiple distinct items.
- Confirm item text/cover orientation is either automatically corrected or manually rotatable.
- Verify the production route, not only the health endpoint.
- For mobile UI, inspect the real route on a phone-sized viewport or probe CSS/HTML markers for the deployed bundle.

## Mobile UI details DJ responded well to

- Mobile-first grid, roughly 3x3/3x4 visible on screen where possible.
- Green check and red X actions in corners.
- Corner actions should be transparent outlined circles when they overlay images, so the image remains visible.
- Center tap should enlarge the item rather than toggling a decision.
- Keep headers and instructional text compact/non-sticky on mobile so the gallery starts near the top.

## Pitfalls

- Do not claim crops are corrected from code-level intent alone. Inspect actual output images.
- Do not rely on a health endpoint for UI/deployment verification; probe the real secret/user route and assets.
- Do not hard-code manual crop boxes as the long-term solution when many items come from floor/table photos.
- Cropping and orientation are separate problems. A good crop generator can still produce sideways text; provide rotation controls or a separate OCR/vision orientation pass.
