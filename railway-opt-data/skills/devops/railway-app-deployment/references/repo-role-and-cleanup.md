# Repo role and cleanup notes

Use this when a user asks to build something locally, put it on GitHub, and deploy it to Railway.

## Key rule

Do not assume the first GitHub repo you find is the deploy source of truth. Some Hermes setups have:

- a *runtime/state backup* repo that captures artifacts and snapshots
- a separate *deployable app* repo that Railway actually builds from

If the running Railway service does not change after a push, verify the deployed service's connected repo/branch before making more code changes.

## Quick checks

- Confirm local repo role with `git remote -v` and the project docs.
- Confirm Railway's connected source in service settings or via API/GraphQL.
- Push only to the repo/branch the service actually watches.
- If code was staged in a temporary or wrong repo, move or cherry-pick the needed files into the real deploy repo.
- After mirroring artifacts into GitHub, remove local scratch copies unless the user asked to keep them.

## Pitfall

A successful GitHub push does not prove Railway deployed the app. It only proves the source repo changed.
