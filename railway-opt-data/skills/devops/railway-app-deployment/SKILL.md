---
name: railway-app-deployment
description: "Deploy web apps to Railway: CLI auth, project/service setup, Postgres, env vars, health checks, migrations, and verification."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [railway, deployment, postgres, nextjs, prisma, auth, devops]
    related_skills: [github-auth, github-repo-management, cron-job-design]
---

# Railway App Deployment

## When to Use

Use this skill when deploying or troubleshooting a web app on Railway, especially:

- creating/linking Railway projects or services
- provisioning PostgreSQL
- setting app environment variables
- deploying Next.js/Node apps
- running migrations/seeds after deploy
- verifying health checks
- setting up cron/backup jobs tied to Railway-hosted apps

## Core Workflow

1. **Verify local build first**

   ```bash
   npm run test
   DATABASE_URL=postgresql://user:pass@localhost:5432/app SESSION_SECRET=dev-secret npm run typecheck
   DATABASE_URL=postgresql://user:pass@localhost:5432/app SESSION_SECRET=dev-secret npm run build
   git status --short
   ```

2. **Authenticate Railway**

   Check status:

   ```bash
   railway whoami 2>&1 || true
   ```

   Preferred for automation/headless environments:

   ```bash
   export RAILWAY_API_TOKEN='<token>'
   railway whoami
   ```

   Some older docs/scripts use `RAILWAY_TOKEN`, but CLI v5 expects `RAILWAY_API_TOKEN` for token auth. Normalize user-provided token names this way:

   ```bash
   export RAILWAY_API_TOKEN="${RAILWAY_API_TOKEN:-${RAILWAY_TOKEN:-}}"
   ```

   Some CLI versions also accept interactive/token login commands, but do not rely on them in headless contexts:

   ```bash
   railway login --token "$RAILWAY_API_TOKEN"
   ```

3. **Avoid repeated browserless auth loops**

   `railway login --browserless` may require an interactive terminal and can expire if the URL/code is not approved promptly. In bridged/headless contexts, try browserless once; if it expires or only shows a spinner, switch to token auth. Do not keep spawning stale login waiters.

   Cleanup:

   ```bash
   pkill -f 'railway login' || true
   ps -ef | grep -E 'railway login' | grep -v grep || true
   railway whoami 2>&1 || true
   ```

4. **Create/link project and service**

   Typical commands vary by Railway CLI version; check help first:

   ```bash
   railway --help
   railway init --help
   railway link --help
   ```

   Common flow:

   ```bash
   railway init
   railway link
   ```

5. **Provision PostgreSQL**

   ```bash
   railway add --database postgres
   railway variables
   ```

   Confirm `DATABASE_URL` is available to the app service.

6. **Set required env vars**

   Example for a Next.js/Prisma app:

   ```bash
   railway variables set NODE_ENV=production
   railway variables set SESSION_SECRET='<long-random-secret>'
   railway variables set GOOGLE_SHEETS_TOKEN_PATH=/opt/data/google-accounts/personal/google_token.json
   railway variables set GOOGLE_CLIENT_SECRET_PATH=/opt/data/google_client_secret.json
   ```

   Do not print secrets back to the user.

7. **Deploy**

   ```bash
   railway up
   ```

   For service-specific deploys, prefer the current CLI's help output. In Railway CLI v5, `railway up --service <name> --detach` works, while some subcommands such as `railway status --service <name>` may reject `--service` even though older scripts used it. If a status flag fails, fall back to `railway status` plus direct app-domain verification rather than treating the deploy as failed.

8. **Run migrations/seeds**

   Prefer Railway-executed commands so they use production env vars:

   ```bash
   railway run npx prisma migrate deploy
   railway run npx prisma db seed
   ```

   If the app has no migration files yet, generate/commit them before deploying.

9. **Verify**

   ```bash
   railway status
   railway domain
   curl -fsS https://<deployed-domain>/api/health
   ```

   Then verify a real app action if possible: login, create a record, and check DB-backed dashboard output.

## `railway.toml` Template

```toml
[build]
builder = "NIXPACKS"
buildCommand = "npm run build"

[deploy]
startCommand = "npm run start"
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

## Pitfalls

- **Browserless login is not enough in headless chat environments.** If it waits/spins or expires, switch to `RAILWAY_API_TOKEN`; do not loop.
- **CLI token variable differs by version.** Railway CLI v5 uses `RAILWAY_API_TOKEN`; normalize `RAILWAY_TOKEN` into it when users paste a token under the older name.
- **Linked service display can be misleading.** `railway status` may show a linked service that differs from the service you intend to mutate. Before changing volumes/variables, confirm the target service by command output or use service-specific flags where supported.
- **Deploy only after local verification.** Tests/typecheck/build should pass before `railway up`.
- **Secrets must be set as Railway variables, not committed.** Keep OAuth tokens/client secrets on persistent volumes or Railway secret storage.
- **Postgres must be provisioned before Prisma deploy.** `DATABASE_URL` needs to exist in the app service.
- **Health check path must exist.** Add a simple `/api/health` route before setting `healthcheckPath`.

## Verification Checklist

- [ ] `railway whoami` succeeds
- [ ] project/service linked
- [ ] Postgres provisioned and `DATABASE_URL` visible
- [ ] required env vars set
- [ ] app deployed with `railway up`
- [ ] migrations/seeds complete
- [ ] `/api/health` returns success
- [ ] real DB-backed app action verified

## References

- `references/nextjs-login-debug.md` — Railway + Next.js production login probes for staged-only fixes, deployed JS chunk inspection, API/session verification, and CLI v5 token quirks.
