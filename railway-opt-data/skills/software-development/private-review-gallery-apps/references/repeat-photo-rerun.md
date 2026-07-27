# Repeat Photo Rerun for Existing Review Gallery Apps

Use this when DJ has an existing working private gallery sorter and sends a new photo/set for the same workflow.

## Key lesson

Do not treat this as a new-app deployment by default. If the existing app already has crop generation, shared decisions, contact sheet, admin/activity, and Railway hosting, the fast path is to replace/add the photo input and rerun the crop manifest pipeline.

## Example: book-sorter-mvp new books photo

Existing repo/service:

- Repo: `djm-new/book-sorter-mvp`
- Local path: `/opt/data/projects/book-sorter-mvp`
- Railway service: `book-sorter` in `chief-cloud`
- Live route: `https://book-sorter-production.up.railway.app/books/4f8b2d7c`

Rerun shape:

```bash
cd /opt/data/projects/book-sorter-mvp
mkdir -p sample-images
rm -f sample-images/*.jpg
cp /path/to/new-photo.jpg sample-images/01.jpg
/opt/hermes/.venv/bin/python scripts/generate_floor_hue_crops.py
```

For a new photo where every item is already upright, remove stale title/rotation overrides or ensure the generated manifest has all `rotation: 0`.

Verify locally:

```bash
/opt/hermes/.venv/bin/python -m unittest discover -s tests -v
/opt/hermes/.venv/bin/python - <<'PY'
import json
from pathlib import Path
m=json.loads(Path('sample-crops/manifest.json').read_text())
print(len(m['items']), sorted({x['rotation'] for x in m['items']}), sorted({x['source'] for x in m['items']}))
PY
```

Generate and visually inspect a quick contact sheet before claiming completion. Confirm:

- every crop is a real item, not floor-only;
- each crop has one clear primary item;
- no unwanted rotation is applied;
- manifest count matches visible expectation.

Deploy if auto-deploy does not fire:

```graphql
mutation($serviceId: String!, $environmentId: String!, $commitSha: String!) {
  serviceInstanceDeployV2(serviceId: $serviceId, environmentId: $environmentId, commitSha: $commitSha)
}
```

Then poll `deployment(id:)` until `SUCCESS` and verify production:

- `/health` returns 200
- review route returns 200
- contact sheet returns 200
- admin route returns 200
- `/sample-crops/manifest.json` has expected `generatedBy`, item count, sources, rotations
- at least one `/sample-crops/...jpg` loads as a real item crop

If the old review decisions are no longer applicable, clear them after deploy:

```bash
curl -X DELETE https://<domain>/api/decisions
```

## Pitfall

If a push succeeds but live assets do not update, check Railway `repoTriggers`. The service may still be deployable from a GitHub commit via `serviceInstanceDeployV2` even when auto-deploy triggers are missing.
