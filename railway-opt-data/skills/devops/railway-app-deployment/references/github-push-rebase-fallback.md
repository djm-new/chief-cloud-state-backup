# GitHub push/rebase fallback

Use this when a deployment fix is committed locally but `git push` is rejected because the remote has new commits.

## Sequence

1. Authenticate with a token-backed remote URL.
2. Fetch the remote branch.
3. Rebase local `main` onto `FETCH_HEAD`.
4. Push again.

## Why this matters

- It preserves the user's recent remote changes.
- It avoids force-pushing over work that landed while the local branch was being edited.
- It is a good default for single-branch deployment repos where the goal is to get the fix live quickly and safely.

## Checklist

- Verify `git status --short --branch` first.
- If `main` is ahead of `origin/main`, push may still be rejected if the remote moved.
- Rebase before pushing rather than creating a second divergent fix commit.
