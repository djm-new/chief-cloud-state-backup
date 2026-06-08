# Chief Alert Triage for DJ

This note captures DJ's preferred alert semantics for Chief health/ops messages.

## Required triage states

Every alert must be one of:

1. **OK** — everything is fine. No DJ action. Prefer silence in recurring monitors.
2. **Warning** — something is off, but not broken yet. Must say what is wrong *and* what DJ needs to do.
3. **Broken** — something is broken. Must say what is broken *and* what DJ needs to do now.

## Formatting rules

- Do not combine a scary heading with `DJ action: none`.
- If the issue is benign or already handled automatically, keep it out of DJ-facing alerts.
- If an alert is emitted, the action must be concrete and human-readable:
  - good: `DJ action: restart the gateway if messages stop arriving.`
  - bad: `DJ action: review logs.`
- If the correct action is actually for Hermes, say that explicitly:
  - `DJ action: none. Hermes should fix this.`

## Example of a benign gateway log line

`Another gateway instance (PID 1) started during our startup. Exiting to avoid double-running.`

This is usually **OK**, not broken:

- it means a duplicate startup was detected and intentionally prevented
- it only matters if message flow is actually interrupted or the gateway is flapping
- do not page DJ for this line by itself

## Example of a warning that needs action

If a recurring health job sees a non-fatal problem that may become an outage, report it as a warning and name the next step.

Example shape:

- `Warning: Telegram confirmations are failing to send formatted follow-up text.`
- `DJ action: none. Hermes should patch the message formatter.`

## Example of a broken state that needs action

If the gateway is down, stuck, or dropping delivery, say so plainly:

- `Broken: gateway process missing.`
- `DJ action: restart the gateway now.`

## Operational takeaway

For recurring monitors, prefer:
- silent on OK
- warning/broken only when actionable
- explicit, concrete action text
- no raw log tail unless it explains the problem
