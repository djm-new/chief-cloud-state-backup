# Stable Decision Keys for Review Gallery Apps

## Lesson

Do not use browser-computed perceptual hashes as the primary key for shared decisions. In the Book Sorter workflow, Sandra's phone saved decisions successfully, but another browser did not show the same decisions because the client-side average hash differed across devices/image decoding paths. The server had the decisions; the lookup key was unstable.

## Durable pattern

Use manifest item IDs as the canonical decision key:

```json
{
  "01-01": {"decision": "discard", "rotation": 90, "updatedAt": "..."},
  "01-02": {"decision": "keep", "rotation": 90, "updatedAt": "..."}
}
```

Keep perceptual hashes only as optional metadata for duplicate grouping or legacy migration:

```json
{
  "itemId": "01-01",
  "hash": "010011...",
  "decision": "keep"
}
```

## Migration pattern

When fixing an existing app that keyed decisions by hash:

1. Load `sample-crops/manifest.json` and any stored decisions from `/api/decisions` or the volume JSON.
2. For each manifest item, map legacy hash decisions to `item.id` when possible.
3. Preserve decision fields such as `decision`, `category`, `rotation`, and `updatedAt`.
4. Write the migrated stable-ID records back to the server/volume.
5. Keep a temporary fallback lookup in UI code: `decisions[item.id] || decisions[legacyHash]` so old records still render.
6. Verify production, not only local code:
   - review HTML contains stable-ID save/load code
   - contact sheet uses stable-ID lookup
   - `/api/decisions` contains item IDs such as `01-01`
   - counts in API match counts rendered in contact sheet

## Implementation hints

- Save/update decisions with `item.id` as the storage key.
- Duplicates can still share a `groupId`, but the group should expand to stable item IDs when saving.
- Contact sheet pages should never rely solely on recomputing client-side hashes to match decisions.
- If using localStorage as fallback/cache, namespace it by project and version, but treat server-side item IDs as source of truth.
