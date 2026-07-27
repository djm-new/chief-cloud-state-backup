# HealthOS cron auth pattern

Session lesson:
- A nightly backup job that logs into the app with a human password is brittle if that password is meant to be rotated after first login.
- If the backup must call a public API endpoint, prefer a *dedicated backup secret* (`HEALTHOS_BACKUP_PASSWORD` or similar) rather than a user-facing password.
- Better still: expose an internal backup entrypoint or service-token path that bypasses the human login flow entirely.

Recommended pattern:
1. Keep the human login flow for humans.
2. Give cron a separate secret, stored as an env var.
3. Have the cron wrapper and the app auth path agree on that dedicated secret.
4. Keep success silent; fail with the first actionable message only.

What not to do:
- Do not hardcode a one-off app password in the cron script if the app status doc says it should be rotated.
- Do not rely on a credential that is expected to change as part of normal security hygiene.

Verification checklist:
- Cron wrapper can authenticate without using the human password.
- The secret is sourced from env, not embedded in the script.
- The job is still silent on success.
- The backup endpoint does not require extra UI/browser steps."