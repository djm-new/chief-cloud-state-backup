# Telegram topic replies vs cron deliveries

If a user says a Telegram topic is "not replying," first separate two cases:

1. **Live gateway conversation**
   - A normal message in a Telegram topic should generate a response from the gateway session.
   - Check gateway logs for `inbound message` and `response ready`.

2. **Cron delivery / scheduled job**
   - Cron jobs are intentionally silent on OK.
   - A `no_agent` job that exits with no stdout will produce no Telegram reply.
   - That is correct behavior for monitors and rollups.

Debug sequence:
- Identify the exact topic/thread ID.
- Check whether the message hit the gateway conversation path or a cron job.
- If it is a cron job and the user expected a chat response, rename/re-route the job so the topic name does not imply live conversation.
- If it is a live conversation, inspect the gateway logs for a model/provider failure or topic mapping issue.
