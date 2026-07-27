# Service domain discovery for Railway apps

Use this when you need the live URL for a Railway service and the dashboard or instance query doesn't immediately show it.

## Key observations

- `serviceInstance.latestDeployment.status` can be `SUCCESS` before the domain has been surfaced in `domains.serviceDomains`.
- For a service with no attached domain, `serviceDomainCreate` can create the default `*.up.railway.app` URL.
- `serviceConnect` accepts `repo` and `branch` in its input; the repo format is `owner/repo`.
- `serviceInstanceDeployV2` currently takes top-level arguments (`serviceId`, `environmentId`, optional `commitSha`), not a `ServiceInstanceDeployV2Input` object. If you omit `commitSha`, Railway may redeploy the previous commit even after you pushed a newer one; pass `git rev-parse HEAD` explicitly when forcing a known GitHub revision.
- If Python `urllib` gets a 403 while `curl` succeeds against the same GraphQL endpoint/token, use `curl` for the deploy automation rather than treating the token as invalid. Verify auth with a simple `{ me { id email } }` GraphQL read first.

## Useful GraphQL snippets

### Inspect the service

```graphql
query($e:String!, $s:String!) {
  serviceInstance(environmentId:$e, serviceId:$s) {
    latestDeployment { id status }
    domains {
      serviceDomains { id domain syncStatus targetPort }
      customDomains { id domain syncStatus targetPort }
    }
  }
}
```

### Create the Railway domain if needed

```graphql
mutation($input: ServiceDomainCreateInput!) {
  serviceDomainCreate(input: $input) {
    id
    domain
    syncStatus
    targetPort
  }
}
```

Example variables:

```json
{
  "input": {
    "environmentId": "<env-id>",
    "serviceId": "<service-id>",
    "targetPort": 8080
  }
}
```

### Connect a GitHub repo

```graphql
mutation($id: String!, $input: ServiceConnectInput!) {
  serviceConnect(id: $id, input: $input) {
    id
  }
}
```

Example variables:

```json
{
  "id": "<service-id>",
  "input": {
    "repo": "owner/repo",
    "branch": "main"
  }
}
```

### Force deploy a specific commit SHA

Use this after pushing to GitHub when you need Railway to deploy the exact current commit instead of accidentally rebuilding an older successful deployment.

```graphql
mutation Deploy($serviceId:String!, $environmentId:String!, $commitSha:String) {
  serviceInstanceDeployV2(serviceId:$serviceId, environmentId:$environmentId, commitSha:$commitSha)
}
```

Example variables:

```json
{
  "serviceId": "<service-id>",
  "environmentId": "<env-id>",
  "commitSha": "<git-rev-parse-HEAD>"
}
```

Poll the returned deployment id:

```graphql
query($id:String!) {
  deployment(id:$id) { id status meta }
}
```

Confirm `meta.commitHash` equals the SHA you requested before verifying the live route.

## Verification

After a deploy, verify all three:

- the deployment status is `SUCCESS`
- the service has a domain
- the actual user route and an asset route both return 200

For secret-link apps, don’t stop at `/health`; check the real route and a linked asset/sub-route too.
