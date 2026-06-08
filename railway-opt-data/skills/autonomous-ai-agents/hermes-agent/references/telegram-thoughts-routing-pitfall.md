# Telegram thoughts-routing pitfall

This note captures two related gotchas from the Daily Brain Dump / Top of Mind flow.

## 1) "Add to top of mind" means the Google Doc, not the session todo list

When DJ says things like:

- `add to top of mind XM comp`
- `add XM comp to top of mind`
- `top of mind: ...`

the action should be to update the Daily ToM Google Doc via the deterministic helper (`/opt/data/scripts/daily-tom-add.py`) and then confirm the actual Google Docs result. Do **not** satisfy the request by only adding a temporary in-session todo or by saying it is "added" when the document was not touched.

Useful behaviors:

- If the item already exists, report `already_present` and say it is already in the document.
- If the item is new, write to the correct group (`Professional`, `Professional - MENA`, `Personal`, etc.) and return the doc-side confirmation.
- Keep the session todo board separate; it is only a working scratchpad.

## 2) Live Daily Brain Dump vs capture-only topics

If a Telegram topic is being used as the live Daily Brain Dump chat, do not let capture logic silently swallow the message and leave DJ without a reply. The channel should either:

- capture and then fall through to the normal Hermes conversation, or
- be explicitly capture-only and stay silent by design.

Avoid mixing the two modes without an explicit bridge, because it creates the impression that the assistant ignored the message even when the capture succeeded.
