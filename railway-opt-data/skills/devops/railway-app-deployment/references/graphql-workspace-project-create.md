# Railway GraphQL workspace discovery and project creation

Use this when Railway CLI is unavailable/flaky but `RAILWAY_API_TOKEN` or `RAILWAY_TOKEN` can authenticate to `https://backboard.railway.com/graphql/v2`.

## Discover the workspace ID

`projects(first: ...)` may return an empty list even when the token is valid. Query `me.workspaces` directly; in this schema it is a list, not a connection.

```graphql
query {
  me {
    id
    email
    workspaces { id name }
  }
}
```

## Create a project

`projectCreate` requires `workspaceId`; if omitted, Railway returns: `You must specify a workspaceId to create a project`.

```graphql
mutation($input: ProjectCreateInput!) {
  projectCreate(input: $input) {
    id
    name
    environments { edges { node { id name } } }
    services { edges { node { id name } } }
  }
}
```

Variables:

```json
{
  "input": {
    "name": "<project-name>",
    "workspaceId": "<workspace-id>",
    "isPublic": false,
    "defaultEnvironmentName": "production"
  }
}
```

## Private GitHub repo caveat

Creating a project with a private repo source can fail with `Failed to fetch repository files` even when the GitHub token can push to the repo. That usually means Railway's GitHub App lacks access to the private repository. Create the project without repo linkage, then connect the service after fixing Railway GitHub App access, or use an alternate deploy path if available.

## Rate-limit pitfall

Railway can rate-limit project creation attempts: `This workspace allows 1 project per 30 seconds`. Wait and retry; do not create duplicate services/projects while uncertain whether the prior mutation partially succeeded. Re-query projects by workspace/name before retrying.
