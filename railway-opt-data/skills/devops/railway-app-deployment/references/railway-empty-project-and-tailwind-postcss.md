# Railway empty-project + Tailwind/PostCSS deployment notes

## What happened
- The Railway project named `healthos` showed *no services* in the dashboard.
- The real live app was actually running under a different Railway project: `chief-cloud`.
- So, when a user reports "my Railway project has no services" or the expected app is missing, verify the actual live project/service mapping instead of assuming the dashboard project name is authoritative.

## How we confirmed the real service
Use GraphQL to list the project services and compare service names/IDs:

```graphql
query($id: String!) {
  project(id: $id) {
    name
    services {
      edges {
        node { id name }
      }
    }
  }
}
```

If the project is empty, search the repo/docs for the deployed URL, then trace the live service by domain or by known service IDs.

## Build failure pattern
The failing Railway deployment showed this error during `next build`:

- `Error: Cannot find module '@tailwindcss/postcss'`

The build logs showed that Railway was doing a production-oriented install that omitted devDependencies, even though the app’s PostCSS plugin lived in `devDependencies` and `postcss.config.mjs` required it.

## Fix that worked
Set the Railway variable:

```text
NPM_CONFIG_PRODUCTION=false
```

Then redeploy. After that, the build proceeded through:
- `prisma generate`
- `next build`
- static page generation
- successful deployment

## Why this matters
When a Next.js app’s build-time CSS tooling lives in `devDependencies`, Railway’s production install can strip the very package the build needs. In that case, either:
- move the required package to `dependencies`, or
- set `NPM_CONFIG_PRODUCTION=false` for the service so devDependencies are installed during build.

## Verification checklist
- Confirm the project/service mapping by GraphQL, not just the dashboard label.
- Check build logs for missing-module failures before changing app code.
- After changing env vars, redeploy and verify the `latestDeployment.status` becomes `SUCCESS`.
- Verify the live route, not only `/api/health`.
