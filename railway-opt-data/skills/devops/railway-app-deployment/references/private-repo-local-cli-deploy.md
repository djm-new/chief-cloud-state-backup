# Railway private-repo deploy bypass: GraphQL project + project token + `railway up --ci`

Use this when Railway GraphQL/API auth works but GitHub App repo access fails for a private repo, e.g. `Failed to fetch repository files` or `Repository "owner/repo" not found or is not accessible` during repo-backed deploy.

## Pattern

1. Verify account API token works via GraphQL `me` and find the workspace ID:

```graphql
query {
  me { id email workspaces { id name } }
}
```

2. Create the project without a repo source if repo-backed `projectCreate` fails:

```graphql
mutation($input: ProjectCreateInput!) {
  projectCreate(input: $input) {
    id
    name
    environments { edges { node { id name } } }
  }
}
```

Variables:

```json
{
  "input": {
    "name": "<app-name>",
    "workspaceId": "<workspace-id>",
    "isPublic": false,
    "defaultEnvironmentName": "production"
  }
}
```

3. Create a service with a repo source if possible, but do not rely on Railway's GitHub App for deployment if it still cannot fetch the private repo:

```graphql
mutation($input: ServiceCreateInput!) {
  serviceCreate(input: $input) { id name }
}
```

Variables:

```json
{
  "input": {
    "projectId": "<project-id>",
    "environmentId": "<environment-id>",
    "name": "<service-name>",
    "source": { "repo": "owner/repo" },
    "branch": "main"
  }
}
```

4. Create a project token for CLI deploys:

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
    "name": "hermes-<app>-deploy"
  }
}
```

5. Install/use Railway CLI and deploy from the local checkout:

```bash
bash <(curl -fsSL railway.com/install.sh) -y
source "$HOME/.railway/env"
export RAILWAY_TOKEN="<project-token>"
railway up --ci --service <service-id>
```

This uploads the local working tree snapshot and bypasses GitHub App repo-fetch permissions.

6. Create or inspect the public service domain. If edge requests return `502 Application failed to respond` while logs show Uvicorn/app listening and internal `/health` passes, check the domain `targetPort`. Railway may assign `$PORT` such as `8080` even if the service domain was created with `targetPort: 8000`.

Inspect:

```graphql
query($serviceId:String!, $environmentId:String!) {
  serviceInstance(serviceId:$serviceId, environmentId:$environmentId) {
    domains { serviceDomains { id domain targetPort syncStatus } }
  }
}
```

Update target port:

```graphql
mutation($input: ServiceDomainUpdateInput!) {
  serviceDomainUpdate(input:$input)
}
```

Variables:

```json
{
  "input": {
    "serviceDomainId": "<service-domain-id>",
    "serviceId": "<service-id>",
    "environmentId": "<environment-id>",
    "domain": "<domain>.up.railway.app",
    "targetPort": 8080
  }
}
```

7. Verify the real user routes, not just deployment success:

```bash
curl -fsS https://<domain>/health
curl -fsS https://<domain>/
curl -fsS https://<domain>/chat \
  -H 'content-type: application/json' \
  -d '{"message":"smoke test","k":3}'
```

## Pitfalls

- Railway CLI account auth may reject an account API token even when direct GraphQL succeeds. A project token can still work for `railway up --ci`.
- Repo-backed deploy failure is not a hard blocker if local checkout + project token deploy is available.
- `serviceDomainUpdate` currently returns `Boolean!`; do not request subfields from it.
- A successful deployment with passing internal health can still produce edge 502 if the service domain targets the wrong port.
