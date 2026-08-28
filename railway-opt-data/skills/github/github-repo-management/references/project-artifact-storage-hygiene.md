# Project Artifact Storage Hygiene for Hermes/Railway Checkouts

Use when a project produces raw artifacts, fetched media, PDFs, transcripts, or large discovery caches while the durable source of truth is GitHub or the user's Google Drive.

## Rule of thumb

- Treat `/opt/...` and Railway/VM disks as disposable working cache, not as a durable artifact destination.
- Durable project artifacts should end up in GitHub (when appropriate for private repo/source artifacts) or the user's personal Google Drive (for user-facing files, exports, large binaries, or anything the user needs to browse/download directly).
- After pushing, clean or sparsify the local checkout so Railway memory/disk is not consumed by raw artifacts.

## Verification before cleanup

From the repo root:

```bash
git status -sb
git log --oneline -3
git ls-files raw | sed -n '1,40p'
du -h -d 1 . 2>/dev/null | sort -h
```

Only remove/sparsify local raw files after the repo is clean and `main...origin/main` or the intended upstream branch is in sync.

## Sparse checkout to exclude bulky raw artifacts locally

If the raw files are tracked in GitHub but should not occupy local working-tree disk:

```bash
git sparse-checkout init --no-cone
git sparse-checkout set '/*' '!/raw/'
du -h -d 1 . 2>/dev/null | sort -h
git status -sb
```

This removes `raw/` from the local working tree but keeps it in GitHub history.

## Blobless reclone when `.git` is still huge

Sparse checkout removes working-tree files, but `.git` may still contain large historical blobs. If disk still matters, replace the checkout with a blobless sparse clone:

```bash
cd /path/to/parent
mv project project-old-$(date +%s)
git clone --filter=blob:none --no-checkout https://github.com/OWNER/REPO.git project
cd project
git sparse-checkout init --no-cone
git sparse-checkout set '/*' '!/raw/'
git checkout main
du -h -d 1 . 2>/dev/null | sort -h
git status -sb
# after verification only:
rm -rf ../project-old-*
```

For private repos in a headless environment, use a temporary `GIT_ASKPASS` helper with `GITHUB_TOKEN` rather than embedding tokens in remotes or logs (see repo-push-auth.md).

## When to use Google Drive instead

Use Drive for artifacts the user needs to personally browse, download, or share outside GitHub, or for large raw media/binaries that do not belong in repository history. Return Drive `webViewLink`s, not local `/opt/...` paths.

## Pitfalls

- Do not cite `/opt/...` paths as user-accessible deliverables; they are internal implementation details.
- Do not leave large raw downloads in Railway/VM checkouts after the durable copy is pushed or uploaded.
- Do not delete unpushed local artifacts unless they are reproducible cache or already preserved in GitHub/Drive.
