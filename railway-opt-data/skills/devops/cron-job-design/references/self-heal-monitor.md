# Cron self-heal monitor pattern

This note captures the follow-up from the Hermes cron failure where a recurring import-path regression kept requiring manual intervention.

## Goal

Make recurring cron failures *self-repairing* when the fix is deterministic and safe, so the next failure does not require a manual back-and-forth.

## Pattern

- Run a lightweight monitor on a short cadence (for example every 15m).
- Scan recent cron output artifacts for new failures.
- Maintain a last-scan timestamp and a seen-failure fingerprint/set so the monitor only reacts to *new* failures.
- For known, narrow failure classes, apply the fix automatically in the live scripts.
- Emit a single concise Telegram message only when a fix was applied or when the failure is not safely auto-repairable.

## Good auto-repair candidates

- Missing shared helper copied into the script tree.
- Import-path regressions where a script should fall back to a local helper.
- Small deterministic path normalization fixes across mirrored script copies.

## Do not auto-fix

- Auth / token / permission failures that need human confirmation.
- Ambiguous runtime failures without a narrow pattern match.
- Anything that would rewrite large chunks of logic without a regression test.

## Safety rules

- Only patch when the failure signature is exact and well-scoped.
- Re-run a compile or dry-run check after patching.
- Keep the monitor silent when there are no new failures.
- Prefer one combined Telegram alert with "DJ action: none" for successful self-repair.

## Implementation notes

- Keep the monitor in a separate script from the failing cron jobs.
- Use a durable state directory for the fingerprint / seen-set / last-scan timestamp.
- When a fix is applied, update both the live script tree and any mirrored backup copy that the runtime may use.
- This pattern is a good fit for import-path regressions and other deterministic cron breakages.
