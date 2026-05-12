# Chief Cloud State Backup

This private repo is intentionally separate from `djm-new/hermes-agent-backup`.

Why there are two Chief-related GitHub repos:

- `hermes-agent-backup` is for the app/code/deployment side: the Hermes Agent source checkout plus Railway deployment files such as `Dockerfile.railway`, `railway.json`, and `docker/railway-chief-start.sh`.
- `chief-cloud-state-backup` is for selected Railway runtime state from `/opt/data`: cron jobs, safe scripts, selected skills, and curated memory files that Chief may update while running online in Railway.

Both repos are private. The split is not about public vs private. It is about keeping two different kinds of backup separate:

- code/deployment backup = can we rebuild/redeploy Chief?
- cloud-state backup = can we restore what Railway Chief learned/configured while it was running?

Important safety rule: this repo must stay selective. Do not blindly sync all of `/opt/data`.

Never include secrets or raw private history, including:

- `.env`
- `auth.json`
- OAuth/token JSON files
- Google account JSON/token files
- `state.db` and SQLite sidecar files
- `sessions/`
- `logs/`
- platform pairing files
- API keys, bot tokens, or refresh tokens

The Railway sync script should only copy allowlisted safe paths.
