# GitHub ↔ Railway Auto-Deploy Verification

Use this when a Railway service should deploy automatically from GitHub pushes but the live app may still be running an older build.

## What to verify

- The service has a connected GitHub repo.
- Auto-deploy is enabled for the service/environment.
- A recent GitHub push triggered a Railway deployment.
- The latest deployment succeeded and matches the pushed commit.
- The live app responds successfully after deploy.

## Useful GraphQL queries

Use an account token with:

- `Authorization: Bearer <RAILWAY_API_TOKEN>`
- `Content-Type: application/json`
- `User-Agent: Mozilla/5.0`

Railway GraphQL endpoint:

- `https://backboard.railway.com/graphql/v2`

### Service repo trigger check

```graphql
query($pid:String!){
  project(id:$pid){
    id
    name
    services { edges { node { id name repoTriggers { edges { node { id branch repository provider environmentId projectId serviceId } } } } } }
  }
}
```

Confirm the service has a `repoTriggers` edge with:

- `provider: github`
- `repository: <owner>/<repo>`
- expected `branch`

### Auto-deploy status check

```graphql
query($pid:String!,$sid:String!,$eid:String!){
  serviceInstanceAutoDeployStatus(projectId:$pid, serviceId:$sid, environmentId:$eid){
    canEnable
    enabled
    reason
  }
}
```

If `enabled` is `true`, pushes should trigger deployments for that service/environment.

### Recent deployments check

```graphql
query($input:DeploymentListInput!){
  deployments(first:3, input:$input){
    edges{ node{ id status createdAt updatedAt statusUpdatedAt meta } }
  }
}
```

The `meta` blob usually contains:

- `repo`
- `branch`
- `commitHash`
- `commitMessage`
- `configFile`
- `runtime`

Match the top deployment's `commitHash` against the Git commit you pushed.

### Build logs check

```graphql
query($id:String!){
  buildLogs(deploymentId:$id, limit:200){
    timestamp
    severity
    message
    tags { deploymentId deploymentInstanceId environmentId projectId serviceId snapshotId }
  }
}
```

This is the fastest way to find the actual compile or build failure.

### Deployment event / failure inspection

```graphql
query($id:String!){
  deploymentEvents(id:$id, first:20){
    edges { node { id createdAt completedAt step payload { error } } }
  }
}
```

Use this to see which step failed and any error text Railway surfaced.

## Verification flow

1. Push commit to GitHub.
2. Query Railway for the service's `repoTriggers` and `serviceInstanceAutoDeployStatus`.
3. Query recent deployments and confirm the newest deployment references the pushed commit.
4. If deployment failed, inspect `buildLogs` first, then `deploymentEvents`.
5. If deployment succeeded, verify the live URL and health endpoint.

## Notes

- A service can be connected to GitHub and still fail to deploy because the app build is broken.
- Live health returning 200 is not enough for frontend changes; confirm the deployment status is `SUCCESS` and that the latest deployment matches the pushed commit hash.
- `gh` CLI is optional for this workflow; it is not required if Git is already authenticated and Railway is available through CLI or GraphQL.
- Railway CLI is useful, but the GraphQL API is often the most direct way to inspect deploy linkage and status in headless environments.
