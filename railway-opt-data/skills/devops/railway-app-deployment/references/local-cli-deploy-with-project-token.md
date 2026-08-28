# Local CLI deploy with a project token when GitHub App repo access fails

Use this when GitHub push works but Railway cannot fetch a private repo, e.g. GraphQL deploy returns `Repository "owner/repo" not found or is not accessible` or project creation from `repo` returns `Failed to fetch repository files`.

## Pattern

1. Verify Railway account API auth with GraphQL `me`; do not rely only on `railway whoami` because the CLI may reject an account API token while GraphQL works.
2. Discover the workspace ID from `me { workspaces { id name } }`.
3. Create or reuse the project via GraphQL without a repo source.
4. Create the service in that project. If repo-source deploy fails, do not stop there.
5. Create a project-scoped Railway token:

```graphql
mutation($input: ProjectTokenCreateInput!) {
  projectTokenCreate(input: $input)
}
```

Variables:

```json
{
  "input": {
    "projectId": "<project-id>",
    "environmentId": "<environment-id>",
    "name": "hermes-deploy"
  }
}
```

6. Install Railway CLI if needed:

```bash
bash <(curl -fsSL railway.com/install.sh) -y
source "$HOME/.railway/env"
```

7. Deploy from the local checkout using the project token. This bypasses Railway GitHub App repo-read access:

```bash
export RAILWAY_TOKEN="<project-token>"
railway up --ci --service <service-id>
```

## Domain port pitfall

When deploying with `railway up`, Railway may assign `PORT=8080` even if `railway.toml` uses `${PORT:-8000}`. Logs can show the app healthy internally on `0.0.0.0:8080` while the public domain returns 502 because the service domain targets 8000.

Fix by querying/creating/updating the service domain target port to the actual logged port:

```graphql
mutation($input: ServiceDomainUpdateInput!) {
  serviceDomainUpdate(input: $input)
}
```

Variables:

```json
{
  "input": {
    "serviceDomainId": "<domain-id>",
    "serviceId": "<service-id>",
    "environmentId": "<environment-id>",
    "domain": "<domain>.up.railway.app",
    "targetPort": 8080
  }
}
```

Then verify the actual public endpoints with `curl`, not just deployment `SUCCESS`:

```bash
curl -fsS https://<domain>/health
curl -fsS https://<domain>/chat \
  -H 'content-type: application/json' \
  -d '{"message":"smoke test","k":3}'
```

## What to report

If local CLI deploy succeeds, do not describe the GitHub App access failure as blocking. Report it as a wiring issue bypassed by project-token local deploy, and note that auto-deploy from GitHub still needs Railway GitHub App access if desired later.
