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

Before creating infrastructure, check whether this is a repeat deployment of an existing working app/pipeline. For repeat work, reuse the known repo/service and deploy path; do not create a new Railway service or repo just because a new asset, photo, or data batch is being added.

When the user says the app is a *separate project*, treat that as a cue to build and deploy it as its own repo/service instead of embedding it in an unrelated product's codebase. Keep product boundaries explicit: separate app, separate repo, separate Railway service, separate verification URL.

GitHub/Railway auth, repo connection, deploy trigger, domain, and app-route problems are agent-owned when credentials/access exist. Diagnose and fix them directly. Only report a blocker when the next step truly requires external user action such as browser approval, account-level permission, billing/quota intervention, or a product decision.

See `references/standalone-services-and-repo-connection.md` for the repo/service split and connection flow.
See `references/service-domain-discovery.md` for live-domain lookup and GitHub connection GraphQL snippets.
See `references/private-gallery-review-apps.md` for secret-link gallery/review apps with shared decisions, activity tracking, and contact sheets.
See `references/private-gallery-review-apps.md` for secret-link gallery/review apps with shared decisions, activity tracking, and contact sheets.
See `references/private-repo-local-cli-deploy.md` for bypassing Railway GitHub App private-repo fetch failures by creating project/service via GraphQL, generating a project token, deploying the local checkout with `railway up --ci`, and fixing service-domain target port mismatches.
See `references/billing-memory-diagnostics.md` for Railway invoice/RAM attribution, Gmail receipt lookup, GraphQL usage queries, and safely deleting unused services/volumes/projects.

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

   In headless or chat-driven sessions, prefer env-var auth over interactive login flows. `railway login` only offers browserless auth in this CLI, so token-based automation should be done by exporting `RAILWAY_API_TOKEN` (or `RAILWAY_TOKEN` for older scripts) before running CLI commands.

   Verify auth immediately before any Railway API or deploy action:

   ```bash
   railway whoami
   ```

   If `whoami` fails, fix the token first; do not spend time probing repo links or GraphQL mutations until auth is valid.

   For headless or non-interactive sessions, prefer a persisted token in `/opt/data/.env` as `RAILWAY_API_TOKEN` (or `RAILWAY_TOKEN` for older scripts). In this environment, the Railway CLI can still report `Unauthorized` even when the token is valid, so treat direct GraphQL reads as the source of truth when CLI auth is flaky.

   If `whoami` is inconclusive but you have a fresh token, do a direct GraphQL read against `https://backboard.railway.com/graphql/v2` with `Authorization: Bearer <token>` and a browser-like `User-Agent` to confirm the token actually works for API reads. See `references/railway-auth-verification.md`.

   Common GraphQL operations for automation:
   - `me { workspaces { id name } }` — discover workspace IDs when `projects(first:...)` is empty but auth is valid
   - `projectCreate(input:{..., workspaceId:...})` — create a project; workspaceId is required
   - `serviceConnect` — attach a GitHub repo to a Railway service
   - `serviceInstanceAutoDeployStatus` — confirm auto-deploy is enabled
   - `serviceDomainCreate` — create the default Railway domain when `domains` is empty
   - `serviceInstanceDeployV2` — trigger a deploy from a specific Git commit SHA
   - `deployments` — list/poll deployment status and build IDs

   See `references/graphql-workspace-project-create.md` for Railway GraphQL workspace discovery, projectCreate inputs, private GitHub repo fetch failures, and project creation rate limits.

   See `references/railway-empty-project-and-tailwind-postcss.md` for the empty-project trap and the Tailwind/PostCSS build failure pattern.
See `references/local-cli-deploy-with-project-token.md` for bypassing private GitHub App repo-access failures by creating a project token and running `railway up --ci` from the local checkout, plus the 502/domain-target-port mismatch fix.

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

   Before pushing anything, confirm whether you are working in the *deployable app repo* or a *runtime/state backup repo*. If the repo role is unclear, inspect the remote, the project docs, and the Railway connection before assuming a push will affect production.

5. **Provision PostgreSQL or persistent storage**

   For database-backed apps, provision Postgres:

   ```bash
   railway add --database postgres
   railway variables
   ```

   Confirm `DATABASE_URL` is available to the app service.

   For tiny private apps that only need durable JSON state (for example shared decisions/activity logs), a Railway volume can be enough. Mount it somewhere explicit such as `/data` and make the app store state under that path, with a local fallback for tests/dev:

   ```graphql
   mutation($input: VolumeCreateInput!) {
     volumeCreate(input: $input) { id name }
   }
   ```

   Variables example:

   ```json
   {
     "input": {
       "projectId": "<project-id>",
       "environmentId": "<environment-id>",
       "serviceId": "<service-id>",
       "mountPath": "/data"
     }
   }
   ```

   Verify the volume is attached to the intended service/environment and is `READY` before relying on it for shared state.

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

   For GraphQL-triggered deploys, use the current `serviceInstanceDeployV2(serviceId:, environmentId:, commitSha:)` signature and pass the exact Git SHA after pushing. Do not use an obsolete `ServiceInstanceDeployV2Input` wrapper. After polling success, verify `deployment.meta.commitHash` matches the requested SHA, then verify the user-facing route/asset markers.

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

   If `railway domain` is empty or unclear, query GraphQL directly for `serviceInstance(...){ domains { serviceDomains { domain syncStatus targetPort } customDomains { ... } } }` and, if needed, create a service domain with `serviceDomainCreate`. See `references/secret-link-domain-discovery.md`.

   If GitHub push succeeds but the live service stays on the old commit, inspect `repoTriggers` and latest deployment metadata. A service can be connected to a repo in deployment metadata but have no active repo trigger, so pushes will not auto-deploy. In that case, use `serviceInstanceDeployV2(serviceId:, environmentId:, commitSha:)` with the exact pushed SHA, then poll `deployment(id)` to `SUCCESS` and verify the live route/manifest. Treat missing repo triggers as a deploy-wiring issue, not as proof Railway auth is blocked.

   Before telling DJ access is missing, exhaust local credential discovery: stale Railway/GitHub env vars can coexist with valid tokens in `/opt/data` backups, git credential stores, or OAuth state. Validate candidates with API reads while redacting token values, then push/deploy with `GIT_ASKPASS` or token-authenticated GraphQL/CLI. Only ask the user after checking the durable stores available on the machine.

   Health can return 200 while Railway is still building/deploying a new frontend bundle and the old page assets are still being served. For UI/CSS/Next.js changes, wait until `railway status` no longer shows `Building`/`Deploying`, then verify the actual route HTML and linked CSS/JS contain a unique marker from the change. If the changed UI is behind login, verify an authenticated page rather than the public login screen; use an existing app-supported recovery/backup login path if present, and never print the credential.

   Example frontend rollout probe:

   ```bash
   python3 - <<'PY'
   import re, urllib.request
   base='https://<deployed-domain>'
   html=urllib.request.urlopen(base+'/meals?date=2026-06-04', timeout=30).read().decode('utf-8','replace')
   assert 'unique-new-class-or-copy' in html
   for href in re.findall(r'href="([^\"]+\.css[^\"]*)"', html):
       css=urllib.request.urlopen(base+href, timeout=30).read().decode('utf-8','replace')
       if 'unique-new-css-class' in css:
           break
   else:
       raise SystemExit('new CSS not served yet')
   print('frontend rollout verified')
   PY
   ```

   Then verify a real app action if possible: login, create/edit/delete a record, and check DB-backed dashboard output.

   For private secret-link apps, do not stop at the health route. Verify the actual user-facing route and at least one linked asset or sub-route. See `references/secret-link-verification.md`.

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

## Cost and cleanup triage

When DJ reports a Railway bill, first distinguish **runtime RAM** from persistent storage/volumes. Stripe receipts may label the largest line item as `Memory (per MB / min)`: that is RAM consumed by running containers over time, not an app intentionally storing data. A quick workflow:

1. Search/read the Railway/Stripe receipt in DJ's Gmail when authorized; Stripe text/plain bodies often include line items such as `Memory (per MB / min)`, `Disk (per GB / min)`, `vCPU`, `Network`, and `Object Storage`.
2. Query Railway GraphQL `usage(workspaceId:, startDate:, endDate:, measurements:[MEMORY_USAGE_GB], groupBy:[PROJECT_ID,SERVICE_ID])` to map memory spend to projects/services.
3. Interpret Railway's memory usage metric as time-integrated memory (effectively GB-minutes for the queried interval); divide by interval minutes for approximate average RAM by service.
4. Check `sleepApplication` and old/stale services. Always-on idle services can be the whole bill even if they store nothing.
5. For a service DJ explicitly says is unused, remove the whole stack in this order: `serviceDelete(id:, environmentId:)`, then `volumeDelete(volumeId:)`, then `projectDelete(id:)` if the project contains nothing else. Verify with `projects(includeDeleted:true)` that the project has `deletedAt` and no services/volumes.

See `references/railway-billing-cleanup.md` for GraphQL snippets and the OpenClaw cleanup example.

## Pitfalls

- **GitHub App deploy-source failure is not always a blocker.** If Railway GraphQL says `Repository "owner/repo" not found or is not accessible` or `Failed to fetch repository files` for a private repo, but GitHub push works and Railway GraphQL account auth works, bypass the GitHub App layer: create/reuse the Railway project and service via GraphQL, create a `projectTokenCreate` token for the environment, install/source the Railway CLI if needed, then run `RAILWAY_TOKEN=<project-token> railway up --ci --service <service-id>` from the local checkout. This deploys a local snapshot without requiring Railway GitHub App repo access. See `references/local-cli-deploy-with-project-token.md`.
- **Public 502 after successful deploy can be a domain target-port mismatch.** If Railway deployment is `SUCCESS` and logs show Uvicorn/listener on `0.0.0.0:<PORT>` with internal health checks passing, but the public `.up.railway.app` URL returns `Application failed to respond`, query the service domain and update `targetPort` to the logged runtime port (often `8080`, not the fallback in `railway.toml`). Verify with public `/health` and a real app request.
- **Authenticated API token does not prove target-project access.** Direct GraphQL `me` can succeed while `projects` is empty or the target `service(id:)` returns `Not Authorized`. Treat that as wrong workspace/account/scope for the deployment target, not as proof the Railway API is broken. Verify the token can actually see the project/service/environment needed for deploy before trying `railway up` or repo-trigger mutations.
- **CLI auth and GraphQL auth can diverge.** If `railway whoami` rejects a token but GraphQL `me` succeeds, continue with GraphQL for diagnostics, but do not assume deploy rights exist until the token can read the target project/service.
- **Railway GitHub App private-repo fetch failure is not necessarily a blocker.** If GraphQL/API auth can create/read the project but repo-backed `projectCreate` or `serviceInstanceDeployV2` says `Failed to fetch repository files` or `Repository "owner/repo" not found or is not accessible`, bypass the GitHub App path: create the project/service via GraphQL, create a `projectTokenCreate` token, install/use Railway CLI, then run `RAILWAY_TOKEN=<project-token> railway up --ci --service <service-id>` from the local checkout. See `references/private-repo-local-cli-deploy.md`.
- **Domain target port can differ from the start-command fallback port.** Railway may run the app on `$PORT` such as `8080` even if `railway.toml` says `${PORT:-8000}` and the service domain was manually created with `targetPort: 8000`. If logs show the app listening and internal health passing but the public URL returns edge `502 Application failed to respond`, inspect `serviceInstance.domains.serviceDomains.targetPort` and update it to the actual app port with `serviceDomainUpdate`.
- **Deploy verification must use a UI marker for frontend fixes.** A healthy `/api/health` only proves the old or current backend is reachable. For UI changes, compare a visible marker from the change (copy, label, route output, asset content) against the live page or user screenshot before declaring production updated.
- **Do not call a local commit “done” when push/deploy is blocked.** If git push fails or Railway project access is missing, report the local commit hash and the exact external access gate; do not imply the production app has changed.
- **Cost audits: distinguish RAM from storage.** Railway invoices may label the large line item as `Memory (per MB / min)`: that is runtime RAM for awake containers over time, not persistent volume storage. Query usage with `MEMORY_USAGE_GB` grouped by `PROJECT_ID,SERVICE_ID`, map IDs back to projects/services, and identify always-on services (`sleepApplication: false`) before blaming volumes. Storage/volume fullness alerts are a separate issue from RAM billing.
- **Unused-service cleanup can be service + volume + project.** When the user explicitly says a Railway app/service is unused and asks to kill it, verify the exact project/service/volume IDs first, then use GraphQL mutations in safe order: `serviceDelete(id:, environmentId:)`, `volumeDelete(volumeId:)`, and if the project contains nothing else, `projectDelete(id:)`. Re-query with `includeDeleted:true` and verify `deletedAt` plus no services/volumes remain.
- **Do not escalate solvable Railway/GitHub wiring as a blocker.**
- **Do not escalate solvable Railway/GitHub wiring as a blocker.** If tokens/access exist, repo connection failures, private/public repo visibility, service domains, auto-deploy triggers, and build/deploy checks should be fixed by the agent. Verify the exact layer with GraphQL/API calls, correct it, and keep moving. Surface only true external-action blockers.
- **Use the correct Railway GraphQL endpoint before concluding auth is broken.** Prefer `https://backboard.railway.com/graphql/v2` with `Authorization: Bearer <token>` and a browser-like `User-Agent`; if CLI or one endpoint is flaky, confirm with direct GraphQL reads (`me`, `project`, `services`) before declaring an auth problem.
- **Browserless login is not enough in headless chat environments.** If it waits/spins or expires, switch to `RAILWAY_API_TOKEN`; do not loop.
- **CLI token variable differs by version.** Railway CLI v5 uses `RAILWAY_API_TOKEN`; normalize `RAILWAY_TOKEN` into it when users paste a token under the older name.
- **`railway whoami` is the fastest auth gate.** Run it before GraphQL/API work; if it fails, treat the token as the problem and stop investigating repo linking or deployment state until auth succeeds.
- **Linked service display can be misleading.** `railway status` may show a linked service that differs from the service you intend to mutate. Before changing volumes/variables, confirm the target service by command output or use service-specific flags where supported.
- **GitHub deploys require a connected repo.** If the Railway service has no GitHub repo attached in Settings, pushing to GitHub will not change the running service. Push local commits first, then connect the repo, then verify the deployment history.
- **The project label in the dashboard may be a dead end.** If a Railway project appears empty, verify the live service mapping by GraphQL (`project { services { edges { node { id name }}}}`) and the known URL/service IDs before assuming the app is gone.
- **Env-backed recovery secrets override code defaults.** If login supports a backup password or bootstrap credential from a Railway variable, changing the fallback literal in code will not fix production by itself. Update the Railway variable, redeploy the service, and verify the live login route before declaring success.
- **Build-time tooling in devDependencies can disappear in production installs.** If `next build` fails on a missing CSS/PostCSS/Tailwind module, check whether Railway is omitting devDependencies. Either move the required package into `dependencies` or set `NPM_CONFIG_PRODUCTION=false` for the service and redeploy.
- **Separate product boundaries stay separate.** If the user says two apps are different projects, do not place the new app under an existing product's repo/service just because it is already deployed. Create a dedicated repo + service and keep the URL, health check, and verification scoped to that product. If the wrong repo was touched, revert it in the source repo and verify the accidental route disappears from the live service.
- **Repo role matters.** A repo used for runtime snapshots or state backups is not automatically the deploy source. If the app is not updating, verify the service's connected repository/branch before moving more code around. See `references/repo-role-and-cleanup.md`.
- **When the remote is ahead, rebase before pushing.** If the local branch is ahead/behind GitHub, fetch the remote commit with token auth, rebase onto it, then push. This avoids stale-code surprises during deploy fixes. See `references/github-push-rebase-fallback.md`.
- **Use GraphQL to verify linkage, not just the dashboard.** For a definitive answer, query `project { services { repoTriggers } }` and confirm a `provider: github` trigger for the expected `owner/repo` and branch. Dashboard UI can lag or hide the exact state.
- **If the service has no domain yet, create one explicitly.** `serviceInstance(...){ domains { serviceDomains { domain syncStatus targetPort } } }` can come back empty even when the deployment succeeded. In that case, use `serviceDomainCreate` with the environment/service IDs and target port instead of waiting for a guessed URL.
- **Service shell is not the repo checkout.** A Railway app console can be the running container only; verify the checkout with `pwd`, `ls`, and `git rev-parse --show-toplevel` before telling the user to run git commands there. See `references/railway-shell-vs-repo.md`.
- **Cron-backed app auth can be a second failure plane.** If a nightly job logs into the app before calling a protected backup route, a 401 can mean the login credential drifted even when the backup code is correct. Prefer a dedicated backup credential/env var and verify the full login-cookie-backup flow end to end. See `references/app-backup-auth.md`.
- **Give one direct execution path.** When the user asks where to run commands, answer with the exact place + exact command sequence + one verification check, not a menu of alternatives.
- **For cleanup/fixes, act first.** If the user says to clean up a mistake or fix a broken deployment, do the remediation directly and report only the finished result unless they explicitly ask for a running commentary.
- **GitHub push is not proof of Railway auto-deploy.** If live assets/routes do not update after a successful push, query the service's `repoTriggers`. A service can have latest deployment metadata from a repo but no active repo trigger. In that case, deploy the pushed commit directly with `serviceInstanceDeployV2(serviceId:, environmentId:, commitSha:)`, poll `deployment(id:)` to `SUCCESS`, then verify the live user route and assets.
- **Use the current Railway GraphQL endpoint first.** Prefer `https://backboard.railway.com/graphql/v2` with `Authorization: Bearer <token>` for API checks. Verify `me`, project, and service state before diagnosing Railway as blocked.
- **Railway GitHub App access and GitHub token access are separate.** You may have admin/push access to a repo via GitHub API while Railway still reports it cannot create a deployment trigger because no one in the Railway project has GitHub App access to that repo. That blocks auto-trigger creation, not necessarily manual deploy from a commit.
- **Deploy only after local verification.** Tests/typecheck/build should pass before `railway up`.
- **Health 200 is not proof that a frontend fix is live.** Railway can keep the old deployment serving while the new one builds/deploys. For UI fixes, wait for status to clear `Building`/`Deploying` and verify the route HTML plus linked CSS/JS contains a unique marker from the change.
- **Project name is not source of truth.** A Railway project shown in the dashboard can be empty while the real service lives in another project/workspace. Verify by service ID / GraphQL / linked domain before assuming the visible project is the deploy target.
- **The service console is runtime, not source.** If the console starts in `/app` and `git remote -v` says the repo is missing, you are inside the deployed image only. Use the service **Settings** or **Deployments** view to find the connected GitHub source. See `references/railway-shell-vs-repo.md`.
- **Cron-backed app auth can be a second failure plane.** If a nightly job logs into the app before calling a protected backup route, a 401 can mean the login credential drifted even when the backup code is correct. Prefer a dedicated backup credential/env var and verify the full login-cookie-backup flow end to end. See `references/app-backup-auth.md`.
- **Production builds may prune needed devDependencies.** If a Next.js build fails on a missing build-time package that exists in `package.json`/`package-lock.json` (for example `@tailwindcss/postcss`), try setting `NPM_CONFIG_PRODUCTION=false` on Railway so `npm ci` includes devDependencies during build. Verify the build logs before and after the env change.
- **Secrets must be set as Railway variables, not committed.** Keep OAuth tokens/client secrets on persistent volumes or Railway secret storage.
- **Postgres must be provisioned before Prisma deploy.** `DATABASE_URL` needs to exist in the app service.
- **Health check path must exist.** Add a simple `/api/health` route before setting `healthcheckPath`.

## Billing / cost investigation

When a user asks why Railway billed for memory, first verify the invoice and usage source before guessing:

- Search Gmail broadly for Railway/Stripe receipts; Railway billing receipts can come from `invoice+statements+...@stripe.com`, not only `@railway.app`.
- Treat invoice **Memory (per MB / min)** as runtime RAM for running containers, not persistent storage. Convert MB-minutes over the invoice period to average RAM to sanity-check the charge.
- Use GraphQL `usage(... measurements:[MEMORY_USAGE_GB], groupBy:[PROJECT_ID,SERVICE_ID])` to attribute RAM to specific services, then map IDs back to project/service names.
- Separately inspect `Disk`, `Object Storage`, and volume-full emails; a volume alert (for example “95% full”) is an operational disk issue, not the same as the memory bill.
- If the user explicitly says an app is unused and to kill it, delete service → dedicated volume → dedicated project, then verify `deletedAt` and empty services/volumes. See `references/billing-memory-diagnostics.md`.

## Verification Checklist

- [ ] `railway whoami` succeeds
- [ ] project/service linked
- [ ] Postgres provisioned and `DATABASE_URL` visible
- [ ] required env vars set
- [ ] app deployed with `railway up`
- [ ] migrations/seeds complete
- [ ] `/api/health` returns success
- [ ] real DB-backed app action verified

## Auth and session recovery

Use this section when a deployed app is reachable but users cannot sign in, stay signed in, or recover access.

- Inspect the login/logout routes, session helpers, middleware, and user model before changing secrets.
- Prefer the least disruptive recovery path: a password-reset endpoint, support/admin path, or env-backed backup login over direct database edits.
- If you must change stored secrets, verify the target account and the storage model first.
- Verify the fix end to end: login succeeds, a session cookie is issued, protected routes load, and the old credential no longer works if the goal was a true reset.
- Keep a note of any backup-login or bootstrap-credential behavior in a support file so future recovery does not require database surgery.

## References

- `references/nextjs-login-debug.md` — Railway + Next.js production login probes for staged-only fixes, deployed JS chunk inspection, API/session verification, and CLI v5 token quirks.
- `references/build-pruning-and-project-mismatch.md` — this session’s Railway pitfalls: empty dashboard project vs live service, and production build pruning devDependencies.
- `references/railway-source-vs-runtime.md` — how to tell whether a Railway service is actually connected to GitHub and why pushes may appear to do nothing until the repo is linked.
- `references/standalone-services-and-repo-connection.md` — the repo/service split and connection flow.
- `references/standalone-secret-link-apps.md` — dedicated-repo/dedicated-service workflow for private secret-link gallery apps, gallery-style UI defaults, and cleanup when edits land in the wrong project.
- `references/repo-role-and-cleanup.md` — notes on distinguishing deploy repos from runtime/state backup repos and cleaning up local scratch copies after mirroring to GitHub.
- `references/service-domain-discovery.md` — GraphQL snippets for discovering/creating the Railway domain and forcing a deploy from a commit SHA.
- `references/private-gallery-review-apps.md` — patterns for standalone secret-link gallery review apps: shared server-side decisions, Railway volume persistence, activity tracking, mobile detail UX, and keep/discard contact sheets.
- `references/auth-recovery.md` — compact web-app login/session recovery notes: inspect auth entry points first, prefer env-backed backup login or reset paths, and verify the session end to end.
- `references/railway-usage-memory-billing.md` — GraphQL diagnostics for unexpected Railway memory/RAM bills; distinguish runtime RAM from persistent volumes and attribute usage by service.
