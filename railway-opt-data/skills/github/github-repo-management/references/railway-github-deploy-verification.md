# Railway + GitHub Deploy Verification

Use this when a repo is supposed to auto-deploy to a Railway service on `git push`.

## What to verify
- GitHub push success does **not** imply Railway auto-deploy is wired up.
- A Railway service can be live via manual/CLI deploys while remaining disconnected from GitHub.
- If the service environment exposes an empty `RAILWAY_GIT_REPO_OWNER` (or similar repo metadata), treat that as a strong sign the GitHub connection is absent.

## Minimal verification sequence
1. Ensure the target branch is already pushed to GitHub.
2. Make a harmless no-op commit and push it:
   ```bash
   git commit --allow-empty -m "chore: trigger deploy verification"
   git push origin main
   ```
3. Poll the live app for a few minutes and compare a stable page marker:
   - HTML build ID / script chunk hashes for Next.js apps
   - any response header or visible marker that should change on a new deploy
4. If GitHub accepted the push but the live app does not change after a reasonable deploy window, the Railway GitHub connection is probably not active.

## Common pitfall
- Checking only the repository remote state is insufficient. You must verify the **running service**.
- A manual deploy from CLI can leave the app healthy while GitHub pushes still do nothing.

## Best next step when disconnected
- Connect the repo from the Railway service settings, or
- use a Railway API token / authenticated Railway CLI flow to connect the repo programmatically.
