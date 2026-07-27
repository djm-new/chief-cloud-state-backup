# Standalone Railway services and repo connection

Use this when an app is *not* part of the existing Chief/Hermes codebase and should not be routed through a different product's repo or service.

## Durable lessons

- If the app is a separate product, give it its own GitHub repo and its own Railway service.
- Do not bury a new app inside an unrelated app's deployment repo just because it is convenient.
- For Railway GitHub deployment, the service connection flow can be done in two steps:
  1. create the service
  2. connect it to the repo/branch

## Practical flow that worked

1. Create the app repo on GitHub.
2. Make sure Railway can access that repo.
3. Create a Railway service for the new app.
4. Connect the service to the repo and branch.
5. Add a health endpoint and a secret link route before verification.

## Notes

- Railway GraphQL exposes separate mutations for service creation and service connection.
- If a repo connection fails with an access error, verify repository visibility and Railway repo permissions before changing app code.
- Use a dedicated project/service when the user says the product is separate.
