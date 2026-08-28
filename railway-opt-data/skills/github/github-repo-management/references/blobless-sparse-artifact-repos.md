# Blobless sparse checkouts for bulky artifact repos

Use this when a repo legitimately stores raw artifacts in GitHub for provenance, but the live VM/Railway checkout should stay small.

## Pattern

1. Push the durable artifacts to GitHub or Drive first.
2. Verify the local repo is clean.
3. Replace the local checkout with a blobless sparse clone that excludes bulky paths such as `raw/`.

```bash
cd /opt/data/projects
mv project project-old-$(date +%s)
git clone --filter=blob:none --no-checkout https://github.com/OWNER/REPO.git project
cd project
git sparse-checkout init --no-cone
git sparse-checkout set '/*' '!/raw/'
git checkout main
du -sh . raw 2>/dev/null || true
git status -sb
```

For private repos in headless environments, use a temporary `GIT_ASKPASS` helper rather than embedding tokens in `origin`.

## Adding a one-off excluded raw file

If sparse checkout excludes `raw/` but a small provenance file must be committed:

```bash
git add --sparse raw/html/source.html
git commit -m "repair source provenance"
git push origin main
git sparse-checkout reapply
```

## Pitfalls

- Do not show `/opt/...` paths to the user as final artifact links; they are VM-local and inaccessible.
- Do not leave bulky raw files in the runtime checkout after pushing them to GitHub/Drive.
- Blobless clones may need auth to hydrate missing objects during `git diff` or checkout; set `GIT_ASKPASS`/credentials before commands that might contact the promisor remote.
