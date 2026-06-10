# Spend billing reconciliation notes

Use this when a spend briefing needs to distinguish *estimated* spend from *truly billed* spend.

## What we observed

- `InsightsEngine.generate(days=...)` can produce a useful session-level estimate and may populate `overview.actual_cost`, but that field is not a guaranteed source of provider billing truth.
- In the Anthropic window we inspected, the session ledger had Anthropic rows with non-zero `estimated_cost_usd` but no trustworthy billed-cost feed, so printing `$0.0000` as billed spend was misleading.

## Rule of thumb

- If the report has estimated spend but the billed-cost field is missing, null, or zero in a window that clearly contains paid usage, render the billed value as `unavailable` rather than `0`.
- Only print a numeric billed total when it comes from a real billing source, not from a placeholder ledger field.

## Reconciliation path for Anthropic

Anthropic’s Admin API provides historical usage/cost data for organizations, including:
- `/v1/organizations/usage_report/messages`
- `/v1/organizations/usage_report/cost`

Notes:
- The Admin API requires an `sk-ant-admin...` key.
- It is not available for individual accounts.
- If the Admin API is unavailable, the spend briefing should continue to show estimated spend and mark billed spend as `unavailable`.

## Practical output guidance

Recommended wording in user-facing reports:

- `Estimated spend: $X.XXXX`
- `Actual billed spend: unavailable`

Avoid:

- `Actual billed spend: $0.0000` when the underlying feed is absent
- implying the system spent nothing just because billing reconciliation is incomplete
- defending a local zero when the user or provider dashboard indicates real billed usage; mark the report incomplete and reconcile against provider billing/admin data first
