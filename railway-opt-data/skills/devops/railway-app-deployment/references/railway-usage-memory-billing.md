# Railway usage and memory billing diagnostics

Use this reference when a user asks why Railway billed them for `memory`, RAM, or unexpected runtime cost.

## Key distinction

Railway `MEMORY_USAGE_GB` is runtime container RAM accumulated over time, not necessarily persistent storage or volume data. A service can create memory cost even if it stores nothing durably, because an always-on container consumes RAM while idle.

Persistent volumes are separate resources. Volume names and sizes help explain storage, but a large Railway memory line item is usually container memory usage by running services.

## GraphQL endpoint/auth

Use the same direct Railway GraphQL pattern as other Railway automation:

- Endpoint: `https://backboard.railway.com/graphql/v2`
- Header: `Authorization: Bearer $RAILWAY_API_TOKEN`
- Include a browser-like `User-Agent`.

Load token from `/opt/data/.env` when available, normalizing `RAILWAY_API_TOKEN` and `RAILWAY_TOKEN`, but never print the token.

## Workspace discovery

The token may return no projects if queried without a workspace. First get the authenticated user and workspaces:

```graphql
query {
  me {
    id
    email
    workspaces { id name team { id name } }
  }
}
```

Then list projects/services for the workspace:

```graphql
query($wid:String!) {
  projects(first:100, workspaceId:$wid, includeDeleted:true) {
    edges { node {
      id name deletedAt createdAt updatedAt
      environments(first:20) { edges { node { id name deletedAt } } }
      services(first:50) { edges { node {
        id name createdAt deletedAt updatedAt
        serviceInstances { edges { node {
          id environmentId deletedAt sleepApplication numReplicas
          latestDeployment { id status createdAt }
        } } }
      } } }
      volumes(first:50) { edges { node { id name createdAt projectId } } }
    } }
  }
}
```

`serviceInstance.sleepApplication: false` indicates the app stays awake continuously and can accrue memory costs even while idle.

## Memory usage attribution

For a month-to-date/top-services breakdown, query usage grouped by project and service:

```graphql
query($wid:String!, $start:DateTime, $end:DateTime) {
  usage(
    workspaceId:$wid
    startDate:$start
    endDate:$end
    includeDeleted:true
    measurements:[MEMORY_USAGE_GB]
    groupBy:[PROJECT_ID,SERVICE_ID]
  ) {
    measurement
    value
    tags { projectId serviceId }
  }
}
```

Interpretation used in practice:

- Sort by `value` descending for the bill drivers.
- Divide each value by total to report share of memory usage.
- If the metric is behaving as GB-minutes over the interval, approximate average RAM as `value / interval_minutes` GB. Label this as approximate unless Railway docs for the billing period confirm the exact unit.

If Railway returns `Too many usage queries are running at once`, retry later or with a narrower/simpler query. Capture the successful query and result, not the transient rate-limit failure.

## Service limits are not actual usage

`serviceInstanceLimits` can show high default caps such as 24 GB memory, but those are limits/capacity ceilings, not proof of usage. Use `usage(... measurements:[MEMORY_USAGE_GB])` for actual bill attribution.

```graphql
query($sid:String!, $eid:String!) {
  serviceInstanceLimits(serviceId:$sid, environmentId:$eid)
  serviceInstanceLimitOverride(serviceId:$sid, environmentId:$eid)
}
```

## Recommended answer shape

For billing shock, be concise and current-state-first:

1. State whether the line item is runtime RAM vs persistent storage.
2. Name the top project/service contributors and their shares.
3. Identify always-on services (`sleepApplication:false`) as likely cause.
4. Do not pause/delete services without approval; explain that changing this can break live apps.
5. Offer concrete next actions: enable sleep for stale/private services, delete unused services, reduce/cap high-RAM apps, or migrate always-on workloads off Railway.
