# Restore guide: Chief Railway cloud-state backup

This private repo backs up selected runtime state from Railway Chief's persistent volume:

`/opt/data`

Use this repo when the question is:

"Can we restore what Railway Chief learned, scheduled, or configured while running online?"

It is separate from `djm-new/hermes-agent-backup`, which backs up the app/code/deployment side.

## What this repo is for

This repo is for selected non-secret runtime state, including:

- `railway-opt-data/cron/jobs.json`
- `railway-opt-data/scripts/`
- `railway-opt-data/skills/`
- `railway-opt-data/memories/` when memory files exist
- `railway-opt-data/SOUL.md` if present

Memory and skills are intentionally included because they are a major part of Hermes' edge: Chief gets better by accumulating useful skills and durable memory over time.

## What this repo must never include

Do not blindly restore or sync all of `/opt/data`. Keep this backup selective.

Never include:

- `/opt/data/.env`
- `/opt/data/auth.json`
- OAuth/token JSON files
- Google account/client-secret/token JSON files
- SQLite databases like `state.db`
- `/opt/data/sessions/`
- `/opt/data/logs/`
- platform pairing files
- API keys, bot tokens, or refresh tokens

## Basic restore flow

Plain-English version:

1. Redeploy Chief's app/code first using `djm-new/hermes-agent-backup`.
2. Confirm Railway project `chief-cloud`, service `chief-gateway`, has a persistent volume mounted at `/opt/data`.
3. Stop or restart the gateway during restore so files are not changing while copied.
4. Copy selected folders from this repo's `railway-opt-data/` snapshot back into `/opt/data/`.
5. Do not copy secrets from GitHub. Recreate secrets from Railway variables or a secure source.
6. Restart Railway service `chief-gateway`.
7. Confirm cron jobs, memory, and skills are visible.
8. Send Chief a Telegram test message.

## Example restore commands from inside Railway SSH

After cloning this private repo somewhere temporary inside the Railway container:

```bash
mkdir -p /opt/data/cron /opt/data/scripts /opt/data/skills /opt/data/memories
cp -a railway-opt-data/cron/jobs.json /opt/data/cron/jobs.json
cp -a railway-opt-data/scripts/. /opt/data/scripts/
cp -a railway-opt-data/skills/. /opt/data/skills/
if [ -d railway-opt-data/memories ]; then cp -a railway-opt-data/memories/. /opt/data/memories/; fi
if [ -f railway-opt-data/SOUL.md ]; then cp -a railway-opt-data/SOUL.md /opt/data/SOUL.md; fi
chmod 700 /opt/data/scripts/*.sh 2>/dev/null || true
```

Then restart Railway Chief and verify:

```bash
hermes cron list
find /opt/data/memories /opt/data/skills -maxdepth 2 -type f | head
```

## Current automatic backup

Railway Chief runs a Hermes cron job that calls:

`/opt/data/scripts/sync_chief_cloud_state_backup.sh`

The job backs up selected `/opt/data` state to this repo daily around 3:15 AM Eastern.
