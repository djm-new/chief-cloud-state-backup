---
name: github-railway-autonomous-deploy
description: "Persistent GitHub↔Railway deploy automation for non-interactive Hermes sessions."
version: 1.0.0
author: Hermes Agent
tags:
  - github
  - railway
  - deploy
  - automation
  - auth
---

# GitHub ↔ Railway Autonomous Deploy

Use this skill when the user wants Hermes to manage a repo/service pair end-to-end without asking for UI clicks or fresh tokens every session.

## What this covers

- pushing code to GitHub
- confirming Railway is connected to the correct GitHub repo
- verifying auto-deploy is enabled
- polling deployment/build status
- checking live health endpoints after deploy
- diagnosing auth issues in headless sessions

## Durable prerequisites

Hermes should have access to:

- a persisted GitHub credential for `git push`
- a persisted Railway token for API/CLI use
- the repo/service mapping for the target app
- the live app URL or health endpoint
- the durable project map at `references/project-map.md`

Recommended persistent locations in this environment:

- `/opt/data/.env` for tokens like `RAILWAY_API_TOKEN`, `RAILWAY_TOKEN`, `GITHUB_TOKEN`
- `/opt/data/.git-credentials` for git HTTPS auth

Always read the project map before deciding what to push, what Railway service to query, or what health URL to verify.

## Default workflow

1. **Confirm the local repo is clean enough to push**
   - `git status --short`
   - `git rev-parse --abbrev-ref HEAD`
   - `git rev-parse HEAD`

2. **Confirm GitHub auth works without prompting**
   - `git ls-remote https://github.com/<owner>/<repo>.git HEAD`
   - if prompting appears, fix credential persistence first

3. **Push to GitHub**
   - `git push origin <branch>`

4. **Confirm Railway linkage and auto-deploy**
   - Prefer direct Railway GraphQL reads in headless sessions when CLI auth is flaky.
   - Use `https://backboard.railway.com/graphql/v2` with `Authorization: Bearer <token>` and a browser-like `User-Agent`.
   - Verify the expected service is connected to the expected GitHub repo and branch.
   - Confirm auto-deploy is enabled.

5. **Poll deployment status**
   - watch the latest deployment until it succeeds or fails
   - if failed, inspect build logs

6. **Verify the live app**
   - hit the health endpoint or a unique route
   - confirm the new behavior is actually live, not just queued

## Railway API notes

For automation, the most useful GraphQL operations are:

- `serviceConnect` — attach a GitHub repo to a Railway service
- `serviceInstanceAutoDeployStatus` — check whether auto-deploy is enabled
- `deployments` — list and poll deployment state
- `buildLogs` — inspect build output when a deploy fails

If `railway whoami` is unreliable in a non-interactive environment, do not block the workflow on it. Use the GraphQL API directly to verify token validity and service state.

## GitHub auth notes

- For git pushes, a stored HTTPS credential is sufficient.
- `gh` CLI is optional, not required.
- Prefer `git credential.helper store --file /opt/data/.git-credentials` in this environment if persistence is needed.

## Pitfalls

- A healthy old deployment does not mean the new commit deployed.
- A connected repo is required for GitHub pushes to trigger Railway deploys.
- CLI login flows that depend on interactive approval are not reliable in headless sessions.
- Always verify the live endpoint after deploy; don’t rely on a push alone.

## Quick checklist

- [ ] GitHub push works without prompting
- [ ] Railway token is available from persistent storage
- [ ] repo is linked to the correct Railway service
- [ ] auto-deploy is enabled
- [ ] latest deployment succeeds
- [ ] live endpoint confirms the new code
