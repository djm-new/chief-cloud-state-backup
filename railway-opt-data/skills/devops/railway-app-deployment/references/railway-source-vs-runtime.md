# Railway source vs runtime: GitHub-connected deploys

Use this note when a Railway app looks healthy but pushing to GitHub doesn't seem to change production.

## Durable lesson

A Railway service only auto-deploys from GitHub when the service is actually connected to the repo in the Railway UI settings.

If the repo is *not connected*:
- pushing to GitHub does **not** change the running Railway service
- the service may still be online from an older deployment path
- the UI can show a live service with no GitHub source attached

## Practical sequence

1. Check the local repo state:
   - `git status`
   - `git log --oneline -5`
   - `git rev-list --left-right --count origin/main...HEAD`
2. Push local commits to GitHub first if the local branch is ahead.
3. In Railway, open the service **Settings** and confirm the repo is connected.
4. Connect the correct GitHub repo and branch if needed.
5. Push again or trigger a redeploy after the connection is in place.

## Verification

- The remote GitHub branch should match local HEAD.
- Railway should show a deployment triggered via GitHub.
- A unique build/deploy commit message should appear in the service deployment history.
