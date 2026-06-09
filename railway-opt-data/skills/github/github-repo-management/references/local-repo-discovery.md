# Local repo discovery in Hermes environments

Use this when a user asks where a project lives, which repo is authoritative, or how two similarly named repos differ.

## Reliable source order

1. **Local project checkout** under `/opt/data/projects/<name>` when present.
2. **Backup mirror** under `/opt/data/github/<repo-name>` or similar mirrored paths.
3. **Project status / handoff docs** such as `PROJECT_STATUS.md`, `README.md`, or restore guides.
4. **Git remote / git log** to confirm the repo's actual owner and purpose.
5. **GitHub API / web** only if local evidence is missing.

## Minimal probe

```bash
# Find likely local checkouts and mirrors
find /opt/data -maxdepth 3 \( -path '*/.git' -o -path '*/PROJECT_STATUS.md' -o -path '*/README.md' \) 2>/dev/null

# Search for the project name across the workspace
search_files --path /opt/data --pattern 'project-name|repo-name' --target content
```

## What to read first

- `PROJECT_STATUS.md` for production URL, GitHub remote, local path, and deployment notes.
- `README.md` / `RESTORE.md` in backup repos for the intended role of the repo.
- `git remote -v` and `git branch --show-current` for the active checkout.

## Practical interpretation

- If the repo is a **workspace / code repo**, expect source, deployment files, and build/config assets.
- If the repo is a **cloud-state backup**, expect selective runtime state, scripts, skills, memories, and restore docs.
- If both exist, treat the code repo as the source of truth for code and the backup repo as the source of truth for durable runtime state.

## Pitfalls

- Do not infer purpose from the name alone; always check the local docs or remote.
- Do not assume the backup mirror is exhaustive; it may intentionally exclude secrets and raw state.
- Do not use GitHub-only inspection when the local checkout already contains the answer.
