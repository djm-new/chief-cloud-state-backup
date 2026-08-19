# Railway billing and memory diagnostics

Use this when a user asks why Railway billed for "memory" or wants unused Railway services shut down.

## Key distinction

Railway invoice line item **Memory (per MB / min)** is runtime RAM, not persistent storage/volume usage. It accumulates for running containers even when the app is idle.

A Stripe/Railway receipt may show, for example:

- `Memory (per MB / min) Qty <mb_minutes> $<amount>`
- `Disk (per GB / min) Qty <gb_minutes> $<amount>`
- `Object Storage` separately

To convert invoice memory quantity to average RAM over the billing period:

```bash
python3 - <<'PY'
mb_min = 283_573_611   # replace with invoice qty
minutes = 31 * 24 * 60 # replace with invoice period duration
print('avg_MB', mb_min / minutes)
print('avg_GiB', mb_min / minutes / 1024)
PY
```

## Gmail receipt lookup

Receipts may come from Stripe, not `@railway.app` directly. Search personal Gmail broadly:

```bash
HERMES_HOME=/opt/data/google-accounts/personal \
/opt/data/google-accounts/.venv/bin/python \
/opt/data/skills/productivity/google-workspace/scripts/google_api.py \
  gmail search '(railway OR railway.app OR railway.com) newer_than:180d' --max 30
```

If `gmail get` returns an empty body for a Stripe invoice, fetch the full Gmail payload with the Google API and inspect `text/plain` parts and PDF attachments. Stripe receipt text often contains the full line items in the `text/plain` part even when the wrapper returns `body: ""`.

## GraphQL usage attribution

Use Railway GraphQL to attribute memory to projects/services. Endpoint:

`https://backboard.railway.com/graphql/v2`

Headers:

- `Authorization: Bearer $RAILWAY_API_TOKEN`
- `Content-Type: application/json`
- browser-like `User-Agent`

Query service-level memory usage for a range:

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

The returned `MEMORY_USAGE_GB` values are time-integrated; divide by elapsed minutes to estimate average GB RAM for the period.

Also inspect whether services are always-on:

```graphql
query($id:String!){
  project(id:$id){
    id name deletedAt
    services(first:50){
      edges{ node{
        id name deletedAt
        serviceInstances{ edges{ node{
          id environmentId deletedAt sleepApplication numReplicas
          latestDeployment { id status createdAt }
        }}}
      }}
    }
    volumes(first:50){ edges{ node{ id name createdAt projectId } } }
  }
}
```

`sleepApplication: false` means the service can continue burning runtime RAM while idle.

## Shutting down an unused stack

When the user explicitly says an app is unused and to kill it entirely, delete in this order and verify:

1. Confirm target project/service/volume names and IDs with a read query.
2. Delete the service:

```graphql
mutation($sid:String!,$eid:String!){
  serviceDelete(id:$sid, environmentId:$eid)
}
```

3. Delete the volume if it is only for that service:

```graphql
mutation($vid:String!){
  volumeDelete(volumeId:$vid)
}
```

4. Delete the project if it exists only to host that unused service:

```graphql
mutation($pid:String!){
  projectDelete(id:$pid)
}
```

5. Verify with `projects(... includeDeleted:true)` that the project has `deletedAt` set and no remaining services/volumes.

## Pitfalls

- Do not confuse invoice "Memory" with volume storage. Volume-full alerts are a separate disk/volume problem.
- Railway dashboard project names can be stale or empty; GraphQL IDs are the source of truth.
- Do not delete shared projects/volumes just because one service is expensive. Delete the project only after confirming it contains only the unused service/volume.
- For user requests to paste raw command output, run the command and return the unmodified output in a code block, without analysis or summary.
