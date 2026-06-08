# Thoughts Repo

Local-first Hermes thought capture and synthesis corpus.

## Privacy decision

This repository is local-first with a private GitHub remote as the approved backup/sync target. The remote must remain private. No public remotes are allowed.

Sensitive directories (`daily/`, `weekly/`, `monthly/`, `quarterly/`, `attachments/`) contain private thought-capture material. Treat the GitHub remote as confidential infrastructure and do not add external collaborators without explicit approval.

This decision was documented before the first commit, per the build spec, and updated after DJ confirmed GitHub should be used for this system.

## GitHub remote setup

Use `scripts/setup_github_remote.py` from this repo after providing a GitHub token with `repo` scope:

```bash
cd /opt/data/thoughts-repo
GITHUB_TOKEN=... ./scripts/setup_github_remote.py hermes-thoughts
```

The setup script creates or reuses a private repo, sets `origin`, and pushes the current branch to `main`. It never prints the token.

## Capture rules

- Daily files are append-only.
- Corrections are new follow-up entries starting with `correction:`; historical entries are never edited.
- A leading `!` is an intensity flag, not a tag/category.
- Synthesis prompts are versioned under `prompts/`; editing a prompt requires a commit.
- Timezone: America/New_York.
