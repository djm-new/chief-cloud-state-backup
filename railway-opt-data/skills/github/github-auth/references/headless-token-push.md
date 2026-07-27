# Headless GitHub push with a temporary token-auth remote

Use this when you have a GitHub token in the environment but no interactive credential helper or `gh` session.

## Pattern
1. Save the current `origin` URL.
2. Temporarily point `origin` at a token-auth URL.
3. Push the branch.
4. Restore the original remote URL.

## Example
```bash
orig=$(git remote get-url origin)
git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/OWNER/REPO.git"
git push origin main
rc=$?
git remote set-url origin "$orig"
exit $rc
```

## Notes
- Keep the token in an environment variable; do not hardcode it into the repository.
- Restore the clean remote URL after the push so later `git remote -v` stays readable.
- This is useful for one-off deploy pushes from headless shells and CI-like environments.
