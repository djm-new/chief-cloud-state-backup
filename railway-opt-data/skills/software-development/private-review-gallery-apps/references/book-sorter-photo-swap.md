# Book Sorter Photo-Swap Workflow

Use this when DJ sends a new floor/table photo for an existing private review gallery app and the app class already works.

## Default approach

Do **not** start by creating a new repo or Railway service. Treat this as an asset/pipeline update unless DJ explicitly asks for a separate standalone project.

1. Locate the existing working app repo/service.
2. Verify the current live secret route and manifest.
3. Save the new source photo into the existing expected input location, e.g. `sample-images/01.jpg`.
4. Rerun the established crop generator.
5. Inspect the generated crop contact sheet visually before claiming success.
6. Update manifest titles/rotations for the new photo; remove stale title/rotation overrides from old photos.
7. Remove stale crop/source folders that are no longer referenced by the manifest.
8. Run local tests and route checks.
9. Commit/push to GitHub.
10. Deploy to Railway and verify the real live route, manifest, contact sheet, and at least one crop asset.

## Rotation rule

If DJ says “all books need to be rotated 90 degrees to the right,” set every manifest item’s `rotation` to `90` and update regression tests to assert `{90}`. Verify production by fetching `/sample-crops/manifest.json` and checking the unique marker/count/rotation set.

## Welcome/intro overlays

If DJ asks to remove a welcome page such as “Hello Sandra,” remove:

- overlay HTML markup
- overlay CSS
- DOM references in JS
- event listeners
- tests that assert the overlay exists

Add/modify a regression test that asserts the welcome copy, overlay IDs, and event listener are absent.

## Blocker discipline

GitHub/Railway/repo connection/deploy/pipeline issues are not user blockers if credentials/access exist. Diagnose and solve the specific layer:

- GitHub repo access
- Railway API auth
- Railway repo trigger connection
- deployment state
- app route/assets
- crop/manifest pipeline

Only surface a blocker if external user action is genuinely required. If Railway has no repo trigger, manual deploy by exact commit SHA can still be enough to ship the change.

## Live verification checklist

- Secret review route returns 200.
- Contact sheet route returns 200.
- Admin route returns 200 if the app has activity tracking.
- Manifest contains the expected `generatedBy` marker, item count, source image(s), and rotation set.
- At least one crop asset returns image content.
- Old welcome copy is absent if removed.
- Saved decisions are reset only when the new item set should start clean.
