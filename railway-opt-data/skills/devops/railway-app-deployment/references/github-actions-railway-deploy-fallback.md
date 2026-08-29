# GitHub Actions Railway deploy when Railway GitHub App cannot access a private repo

Use this when:
- GitHub push succeeds with a PAT/OAuth token.
- Railway GraphQL/API can read the target project/service and local `railway up --ci` works with a project token.
- Native Railway repo-trigger setup fails with errors such as `User does not have access to the repo`, `Repository "owner/repo" not found or is not accessible`, or `Cannot create deployment trigger ... because no one in the project has access to it`.

This is not the same as fixing the Railway GitHub App installation, but it restores future push-to-production automation while keeping the repo private.

## Steps

1. Verify the actual failure plane:

```graphql
mutation($id:String!,$input:ServiceConnectInput!) {
  serviceConnect(id:$id,input:$input) { id name }
}
```

Variables:

```json
{
  "id": "<service-id>",
  "input": {"repo": "owner/repo", "branch": "main"}
}
```

Also try `deploymentTriggerCreate`. If both fail because Railway lacks GitHub repo access, continue.

2. Create a Railway project token for the target project/environment:

```graphql
mutation($input:ProjectTokenCreateInput!) {
  projectTokenCreate(input:$input)
}
```

Variables:

```json
{
  "input": {
    "projectId": "<project-id>",
    "environmentId": "<environment-id>",
    "name": "github-actions-deploy"
  }
}
```

3. Store that project token as GitHub Actions secret `RAILWAY_TOKEN` using the GitHub Actions secrets API. Encrypt with the repo public key; do not print or commit the token.

4. Add `.github/workflows/deploy-railway.yml`:

```yaml
name: Deploy to Railway

on:
  push:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: railway-production
  cancel-in-progress: true

jobs:
  test-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: python -m pytest -q

      - name: Install Railway CLI
        run: |
          bash <(curl -fsSL railway.com/install.sh)
          echo "$HOME/.railway/bin" >> "$GITHUB_PATH"

      - name: Deploy local checkout to Railway
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: $HOME/.railway/bin/railway up --ci --service <service-id>
```

5. Commit and push the workflow.

6. Poll the GitHub Actions run until it completes. If it fails with `railway: command not found`, use the explicit `$HOME/.railway/bin/railway` path as above.

7. Verify production with the app's real product checks, not only `/health`.

## Notes

- This creates push automation via GitHub Actions, not a native Railway repo trigger.
- If the user specifically wants the Railway dashboard repo trigger, they must grant the Railway GitHub App access to the private repo/org. Until then, GitHub Actions + Railway project token is the autonomous workaround.
- Keep the local git tree clean: remove `__pycache__`, `.pytest_cache`, and generated eval/index artifacts unless intentionally changed.
