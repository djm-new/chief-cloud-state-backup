# Podcast digest cron fix

Session lesson:
- The daily podcast digest wrapper was timing out because it chained too much work inside Hermes' 120s cron window.
- The failure mode was: collect known feeds + semantic discovery + scoring + render all in one run.

Durable fix pattern:
- Keep the daily delivery path bounded and conservative.
- Make semantic discovery optional or separate from the daily briefing path.
- Put hard time budgets around collection/discovery steps so a slow upstream source cannot kill the whole digest.
- Prefer delivering a partial-but-valid digest over timing out the whole cron run.

Observed wrapper pattern that worked:
- Daily ET guard in the wrapper.
- Collection step wrapped in `timeout`.
- Semantic discovery disabled by default via an env flag.
- Bigger scoring batches to reduce round-trips.

Checklist for future edits:
- Verify the wrapper still finishes comfortably inside the cron timeout.
- Keep the final digest generation step as the most protected part of the pipeline.
- If semantic discovery is enabled, make it separately bounded and non-fatal to the delivery path.