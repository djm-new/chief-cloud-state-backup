# Repo push/auth checklist for Hermes

Use this when a repo should be visible on GitHub but `git push` is failing or the remote is already set.

## Key idea

A repo can already point to GitHub and still fail to push if the current shell is not authenticated.

## Checklist

1. Verify the remote:
   ```bash
   git remote -v
   ```
2. Verify branch/state:
   ```bash
   git status --short --branch
   ```
3. Verify auth method on the host:
   - `gh auth status` if available
   - otherwise check for `GITHUB_TOKEN` / `GH_TOKEN` in the active environment
   - avoid assuming a token exists just because the repo is on GitHub
4. If the project has an existing deploy/bootstrap script that authenticates `gh` and pushes, prefer that over manual one-off commands.
5. If `git push` says it cannot read the GitHub username/password, treat it as an auth problem, not a remote problem.

## Common Hermes pattern

Some repo bootstrap/deploy scripts are designed to run in Railway/Chief where secrets exist in environment variables. In a plain local shell, those env vars may be absent even though the production environment has them.

## Safe verification

- `git ls-remote origin HEAD` confirms the remote is reachable *with current auth*.
- If that fails with a username/password prompt error, GitHub auth is missing.
- Do not rewrite the remote URL unless the owner/repo itself is wrong.
