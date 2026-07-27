# Secret-link domain discovery and deploy verification

Use this when a Railway service is connected and deployed, but the live URL is unknown or the domain list is empty.

## Key GraphQL patterns

### 1) Read service and domain state

```graphql
query($e: String!, $s: String!) {
  serviceInstance(environmentId: $e, serviceId: $s) {
    latestDeployment { id status }
    domains {
      serviceDomains {
        id
        domain
        syncStatus
        targetPort
      }
      customDomains {
        id
        domain
        syncStatus
        targetPort
      }
    }
  }
}
```

If `serviceDomains` is empty even though the deployment succeeded, the service may simply not have a domain created yet.

### 2) Create a Railway service domain

```graphql
mutation($input: ServiceDomainCreateInput!) {
  serviceDomainCreate(input: $input) {
    id
    domain
    syncStatus
    targetPort
    environmentId
    serviceId
  }
}
```

Variables example:

```json
{
  "input": {
    "environmentId": "<environment-id>",
    "serviceId": "<service-id>",
    "targetPort": 8080
  }
}
```

A successful create often returns the default `*.up.railway.app` domain immediately with `syncStatus: CREATING`, then it flips to `ACTIVE`.

### 3) Trigger a deploy from a known commit

```graphql
mutation($e: String!, $s: String!, $c: String!) {
  serviceInstanceDeployV2(environmentId: $e, serviceId: $s, commitSha: $c)
}
```

This returns a deployment id string. Poll `serviceInstance(...){ latestDeployment { status } }` until it reaches `SUCCESS`.

## Verification flow

1. Query `serviceInstance(...){ domains { serviceDomains { domain syncStatus } } }`.
2. If empty, create the domain explicitly with `serviceDomainCreate`.
3. Trigger the deploy with `serviceInstanceDeployV2` if the latest code hasn't rolled out yet.
4. Verify the secret-link route itself, not just `/health`.
5. Also verify at least one asset or sub-route used by the page.

## Notes

- `serviceConnect` can succeed even when the repo-trigger edge list is not yet populated.
- Domain discovery is separate from GitHub repo connection.
- For secret-link apps, the real test is the user-facing route HTML and a linked asset, not the health endpoint alone.
