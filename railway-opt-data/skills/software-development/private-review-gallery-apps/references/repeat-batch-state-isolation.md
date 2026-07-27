# Repeat Batch State Isolation

Use this when a private review gallery is reused for a new photo/batch while keeping the same app route and stable item IDs like `01-01`, `01-02`.

## Problem

The server can be correctly cleared for a fresh batch while a reviewer browser still shows old keep/discard overlays. The usual cause is flat localStorage state from the previous batch being merged into server state.

Symptoms:

- `/api/decisions` returns `{}` or fewer decisions than the UI shows.
- The gallery shows check/X overlays before anyone has reviewed the new batch.
- The same `01-XX` IDs were reused in the new manifest.
- A user reports black triangles or repeated overlay artifacts; these may be stale discard overlays plus missing SVG path styling.

## Fix pattern

### 1. Namespace client cache by batch/set id

```js
const CURRENT_SET_ID = "kids-books-batch-3-YYYY-MM-DD";
const STORAGE_KEY = `hermes-book-sorter-decisions-v1:${CURRENT_SET_ID}`;
```

Do not use a single permanent key such as `hermes-book-sorter-decisions-v1` for all batches if item IDs are reused.

### 2. Server decisions are authoritative

When `/api/decisions` succeeds, replace local state with server state, do not merge:

```js
state.storage = { ...data.decisions };
saveStorage();
```

Avoid:

```js
state.storage = { ...state.storage, ...data.decisions };
```

If server is empty, merging preserves stale browser choices.

### 3. Clear active decisions only after deploy verification

For a new active batch:

1. Preserve historical Sheet/log state for the completed batch.
2. Deploy the new manifest/assets.
3. Verify the live route and manifest count.
4. `DELETE /api/decisions` to reset the active Railway state.
5. Verify `/api/decisions` returns 0 decisions.

### 4. Style overlay SVGs explicitly

Inline SVG decision overlays need path styling:

```css
.overlay svg path {
  stroke: currentColor;
  stroke-width: 3.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}
```

Without `fill: none`, an X path can render as a filled black polygon/triangle, making stale discard decisions look like identical black crop artifacts.

## Verification

- Live HTML contains the new `CURRENT_SET_ID`.
- Live HTML contains a batch-scoped `STORAGE_KEY`.
- Live HTML contains `state.storage = { ...data.decisions };`.
- Live HTML does not contain `state.storage = { ...state.storage, ...data.decisions };`.
- `/api/decisions` count matches what the initial UI should show.
- If the user reports repeated artifacts, inspect raw crop JPEGs and rendered HTML/CSS before changing crop boxes.
