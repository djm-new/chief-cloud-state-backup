# Railway billing and cleanup triage

Use this when DJ reports a surprising Railway bill or asks to kill unused Railway services.

## What the invoice line items mean

Stripe/Railway receipts can include:

- `Memory (per MB / min)` — container RAM over time. This is usually the big line item for always-on services and is **not** persistent storage.
- `Disk (per GB / min)` — persistent disk/volume usage over time.
- `vCPU (per vCPU / min)` — CPU over time.
- `Network` — bandwidth.
- `Object Storage (per GB-month)` — bucket/object storage.
- `Agent Usage` — Railway Agent usage.

To convert `Memory (per MB / min)` into an intuitive average:

```bash
python3 - <<'PY'
mb_min = 283_573_611  # invoice quantity
minutes = 31 * 24 * 60
print('avg MB:', mb_min / minutes)
print('avg GiB:', mb_min / minutes / 1024)
PY
```

## Find the services causing RAM spend

Use Railway GraphQL directly when the CLI is unavailable or flaky:

```graphql
query($wid:String!,$start:DateTime,$end:DateTime){
  usage(
    workspaceId:$wid
    startDate:$start
    endDate:$end
    includeDeleted:true
    measurements:[MEMORY_USAGE_GB]
    groupBy:[PROJECT_ID,SERVICE_ID]
  ){
    measurement
    value
    tags { projectId serviceId }
  }
}
```

Then divide each `value` by interval minutes to estimate average RAM for that service. Map project/service IDs with:

```graphql
query($wid:String!){
  projects(first:100, workspaceId:$wid, includeDeleted:true){
    edges{ node{
      id name deletedAt
      environments(first:20){ edges{ node{ id name deletedAt } } }
      services(first:50){ edges{ node{
        id name deletedAt
        serviceInstances{ edges{ node{
          id environmentId deletedAt sleepApplication numReplicas
          latestDeployment { id status createdAt }
        } } }
      } } }
      volumes(first:50){ edges{ node{ id name createdAt projectId } } }
    } }
  }
}
```

## Kill an unused stack

If DJ explicitly says the service/project is unused, remove the full stack:

1. Identify the project ID, environment ID, service ID, and volume ID.
2. Delete service first:

```graphql
mutation($sid:String!,$eid:String!){
  serviceDelete(id:$sid, environmentId:$eid)
}
```

3. Delete associated volume(s):

```graphql
mutation($vid:String!){
  volumeDelete(volumeId:$vid)
}
```

4. If the project only existed for that service, delete the project:

```graphql
mutation($pid:String!){
  projectDelete(id:$pid)
}
```

5. Verify:

```graphql
query($wid:String!){
  projects(first:100, workspaceId:$wid, includeDeleted:true){
    edges{ node{ id name deletedAt services(first:20){edges{node{id name deletedAt}}} volumes(first:20){edges{node{id name}}} } }
  }
}
```

Expected result for a fully removed project: `deletedAt` is set, and `services.edges` / `volumes.edges` are empty.

## Pitfalls

- Volume-full emails (for example “service is 95% full”) are disk alerts and may coexist with, but are separate from, high `Memory (per MB / min)` billing.
- Do not delete a shared project if it contains other live services; delete only the target service/volume unless DJ asked to remove the whole project.
- If usage queries return “too many queries running,” retry later or narrow measurements/grouping rather than assuming auth is broken.
