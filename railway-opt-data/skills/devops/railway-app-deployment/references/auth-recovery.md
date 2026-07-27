# Auth Recovery for Web Apps

Use this note when a deployed app's login or session flow is broken and you need to restore access with minimal disruption.

## Core recovery order

1. Inspect the auth entry points first:
   - login route
   - logout route
   - session helpers
   - middleware / route guards
   - user model and password storage

2. Identify the recovery mechanism before changing stored secrets:
   - explicit password reset endpoint
   - admin/support path
   - backup login / bypass account
   - seed or bootstrap credentials
   - direct database update only if the app has no safer route

3. Prefer the least disruptive fix:
   - rotate an env-controlled backup password if the app supports it
   - use a dedicated reset endpoint if available
   - update the stored password hash only when you can verify the target user and auth model

4. Verify the outcome:
   - login succeeds with the new secret
   - session cookie is set
   - protected routes load after login
   - old credentials no longer work if the goal was a true reset

## Pitfalls

- Don’t assume the password is stored in plaintext; inspect the user table or auth model first.
- Don’t overwrite production user records without verifying which account is being targeted.
- Don’t forget session secrets and cookies: a password reset can look broken if the session layer still points elsewhere.
- Don’t stop after finding a bypass path; make sure the user can actually sign in with it.
- If the backup login is env-controlled in production, changing the source-code fallback alone is not enough; update the live secret or variable and redeploy before testing the login route.

## Verification checklist

- Confirm the target username/account.
- Confirm the password hash field or equivalent storage location.
- Confirm the login route accepts the new credential.
- Confirm the session cookie or token is issued.
- Confirm protected pages are reachable after login.
