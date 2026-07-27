# Standalone Secret-Link Apps

Use this workflow when the user wants a new small app that should *not* be folded into an existing product repo/service.

## Default shape

- One dedicated GitHub repo for the app
- One dedicated Railway service for that repo
- One secret user-facing route (not just `/health`)
- `robots.txt` or equivalent noindex protection
- Static assets served explicitly if the UI depends on them

## Recommended flow

1. **Scope the user flow first**
   - Confirm the one-screen action the family member should take.
   - For photo-review tools, default to a mobile-first gallery.
   - Use obvious corner actions for keep/discard and a center-tap enlarge affordance.
   - If orientation is uncertain, add manual rotate controls instead of baking in more code.

2. **Keep repo boundaries explicit**
   - Do not place the new app under an unrelated product just because that product already deploys cleanly.
   - If the app needs to live in GitHub before Railway can connect, use the smallest visibility change necessary for the connection, then keep the app itself behind the secret route.

3. **Implement and verify locally**
   - Start the app locally.
   - Verify the user-facing route, the static asset route, and the health check.
   - For gallery apps, verify the HTML contains the intended controls and the asset routes actually return images.

4. **Deploy to the dedicated Railway service**
   - Connect the dedicated repo to the dedicated service.
   - Trigger a deploy from the app commit, not from some unrelated state repo.
   - Verify the deployed user route, not only the health endpoint.

5. **Clean up mistakes in the source repo**
   - If a feature lands in the wrong project, revert it there rather than leaving it as a parallel copy.
   - After revert, verify the accidental route no longer serves the feature.

## Verification checklist

- Repo name and service name match the new app
- User-facing route works on the live domain
- Asset/static route works
- Health route works
- Accidental cross-project edits are removed from the wrong repo

## Common mistakes

- Using an existing product repo as a dumping ground for a separate app
- Treating `/health` as proof the user flow is ready
- Forgetting to verify a linked asset route
- Leaving accidental edits in the wrong repo after the real app is created
