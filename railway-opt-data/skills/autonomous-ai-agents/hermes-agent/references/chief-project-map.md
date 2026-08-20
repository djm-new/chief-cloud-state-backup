# Chief Project Map

Use when DJ asks where something lives, how repos are organized, or where to find/edit a workflow.

## The Three GitHub Repos

### `djm-new/chief-cloud-state-backup`
**Purpose:** "Can we restore what Chief learned while running?"
- Selective nightly snapshot of `/opt/data` (runs ~3:15 AM ET)
- What's included: cron jobs, scripts, skills, memories, config, SOUL.md,
  podcast digest outputs, briefing calibration, redacted session exports, thoughts-repo corpus
- What's excluded: `.env`, auth tokens, SQLite DBs, sessions/, logs/, caches
- Local clone: `/opt/data/github/chief-cloud-state-backup`

### `djm-new/hermes-agent-backup`
**Purpose:** "Can we rebuild/redeploy Chief?"
- Hermes Agent source checkout + Railway deployment files
- `Dockerfile.railway`, `railway.json`, `docker/railway-chief-start.sh`

### `djm-new/hermes-thoughts`
**Purpose:** "Can we inspect and restore the Daily Brain Dump / thoughts archive directly?"
- Git remote for the local thoughts repo at `/opt/data/thoughts-repo/`
- Contains daily markdown captures, weekly/monthly/quarterly synthesis artifacts when generated, attachments, and redacted session exports intended for private backup
- Treat `/opt/data/thoughts-repo/` as the live source of truth; use the GitHub repo as the private remote/backup mirror

### `djm-new/healthos`
**Purpose:** HealthOS app code
- Next.js/TypeScript/PWA health tracking app
- Local checkout: `/opt/data/projects/healthos`
- Railway service: `healthos` on project `chief-cloud`
- **NOTE: As of last check, Railway healthos service is NOT connected to GitHub.**
  Deployments were done via Railway CLI. Connect repo in Railway Settings to enable auto-deploy.

## The Live Brain (Railway /opt/data)

Primary source of truth — everything Chief knows and does:

- The *runtime-state* source of truth lives in `/opt/data` and its backed-up mirror repo `djm-new/chief-cloud-state-backup`.
- App/code/deployment source belongs in `djm-new/hermes-agent-backup`.
- Treat `/opt/hermes` as scratch unless you have verified it is a checked-in Git repo.

| Path | What lives here |
|---|---|
| `/opt/data/memories/` | DJ's persistent memory (injected every session) |
| `/opt/data/skills/` | Learned skills and procedures |
| `/opt/data/cron/jobs.json` | All scheduled jobs |
| `/opt/data/scripts/` | Utility scripts |
| `/opt/data/thoughts-repo/` | Daily Brain Dump, ToM, weekly/monthly synthesis; git remote `djm-new/hermes-thoughts` |
| `/opt/data/config.yaml` | Model routing, topic overrides, platform config |
| `/opt/data/slack_brief_archive/` | Business briefing history |
| `/opt/data/podcast_digest/` | Podcast workflow state and outputs |
| `/opt/data/projects/healthos/` | HealthOS local checkout (ahead of GitHub) |
| `/opt/data/github/chief-cloud-state-backup/` | Local clone of backup repo |

## Mental Model

```
Railway /opt/data              ← live brain (primary source of truth)
      ↓ nightly backup
chief-cloud-state-backup       ← "what did Chief learn?" (restore target)
hermes-agent-backup            ← "how do we rebuild Chief?" (redeploy target)
healthos                       ← project app code (separate Railway service)
```

## Key Workflows

**Podcast intelligence:** `/opt/data/podcast_digest/` + `/opt/data/scripts/podcast_*.py`
- No separate GitHub repo — lives as local state + backed up in chief-cloud-state-backup

**Daily business briefing:** `/opt/data/slack_brief_archive/` + `/opt/data/scripts/slack_business_brief_*.py`
- Driven by cron jobs, no separate GitHub repo

**HealthOS app changes:** edit `/opt/data/projects/healthos/` → push to `djm-new/healthos`
- Then Railway auto-deploys (once repo is connected) or manual `railway up`
