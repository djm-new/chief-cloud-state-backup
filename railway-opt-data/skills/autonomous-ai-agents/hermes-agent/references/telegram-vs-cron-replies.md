# Telegram topic reply vs cron delivery

If a user says a Telegram topic is "not replying," verify whether the message is:

- a **live gateway conversation** (should generate a response), or
- a **cron delivery / scheduled job** (may intentionally be silent on success).

Useful checks:
- Inspect gateway logs for `inbound message` and `response ready`.
- Inspect cron logs for `empty stdout — silent run` or `[SILENT]`.
- Confirm the exact topic/thread ID before assuming a model failure.

If the thread is a live conversation and still silent, check for model/provider errors or a bad topic mapping. If it is a cron job, silence on OK is expected.
