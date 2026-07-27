# App backup auth troubleshooting

When a system logs into a web app and then immediately calls a protected backup/export route, treat auth as a separate failure plane from the backup logic itself. The same pattern applies to human login flows, cron jobs, and support recovery logins.

## Pattern

- `POST /api/auth/login` returns `401` when the supplied password no longer matches the stored hash or backup secret.
- If login succeeds but backup fails, inspect the session/cookie or the backup route's authorization check.
- If both login and backup succeed manually, the cron job may be carrying stale credentials or malformed JSON/body encoding.

## Reusable fix pattern

1. Give the cron path a *dedicated backup secret* instead of reusing the human password.
2. Let login accept that dedicated secret only for the backup username/account.
3. Pass the secret via env var in the wrapper script.
4. If production reads the secret from an environment variable, update the live variable and redeploy before testing the login route.
5. Verify the full flow with a cookie jar:
   - login → cookie
   - backup request with cookie → `200` and expected sheet/url payload

## Session recipe

- Login endpoint: `POST /api/auth/login`
- Backup endpoint: `POST /api/backup`
- Successful manual verification should prove both steps independently and together.

## Pitfall

Do not assume a backup failure means the export code is broken just because the error surfaced at the backup request. A login `401` upstream can mask a perfectly healthy backup route.