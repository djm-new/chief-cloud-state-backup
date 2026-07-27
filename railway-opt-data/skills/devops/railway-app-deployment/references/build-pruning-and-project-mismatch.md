# Railway build pruning and project-mismatch notes

This session surfaced two durable Railway troubleshooting patterns:

## 1) Empty dashboard project vs real live service
- The project named `healthos` was empty in the dashboard.
- The actual live app was running under `chief-cloud`.
- Always confirm the target service with one of:
  - service ID
  - GraphQL `project(id)` / `serviceInstance(...)`
  - live domain verification
- Do not assume the most obvious project name is the deploy target.

## 2) Build-time devDependency pruning
- Production build failed on a missing module during `next build`:
  - `Cannot find module '@tailwindcss/postcss'`
- The package existed in `package.json` and `package-lock.json`, but Railway’s build was omitting devDependencies.
- Fix used:
  - set `NPM_CONFIG_PRODUCTION=false` on the Railway service
  - redeploy
- After that, the Next.js build completed successfully.

## Verification pattern
- Check deployment logs for the exact failure line before changing config.
- After any env/config change, redeploy and verify:
  - deployment status becomes `SUCCESS`
  - `/api/health` responds
  - the actual user route renders, not just the health endpoint
