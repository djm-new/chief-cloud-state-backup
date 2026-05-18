# Slack monitoring and digest setup notes

Use this when the user wants Hermes/Chief to monitor Slack proactively.

## Key discovery pattern

1. Verify gateway/platform status with the installed Hermes binary. In containerized installs, the launcher may be `/opt/hermes/.venv/bin/hermes` rather than `hermes` on PATH.
2. List known messaging targets with the messaging/send tool if available; this shows channels the gateway already knows about.
3. Check gateway state/channel directory under the configured `HERMES_HOME` (commonly `/opt/data` in Docker):
   - `/opt/data/gateway_state.json`
   - `/opt/data/channel_directory.json`
   - `/opt/data/logs/agent.log`
4. Load Slack tokens from the Hermes `.env` file only inside scripts/process env; do not print token values.
5. Use `slack_sdk.web.async_client.AsyncWebClient` and `auth_test()` to verify the bot/workspace.
6. `conversations.list` can show many public channels, but `conversations.history` only succeeds where the bot/user token has access. A `not_in_channel` error means the bot can see the channel exists but cannot read messages there.

## Access model pitfall

Slack bot tokens do not automatically read every channel in the workspace. For channel monitoring:

- Bot token + Socket Mode can receive messages only for channels/events the app has access to.
- `conversations.history` for a public channel fails with `not_in_channel` unless the bot is a member.
- To monitor important channels quickly, ask the user to invite the bot in Slack: `/invite @<bot_name>`.
- Bulk-joining public channels is visible/noisy and should require explicit user approval.
- If the requirement is "monitor everything the user can see," prefer a user-level OAuth token with appropriate scopes rather than bot-channel invites.

## Digest job pattern

For low-noise proactive monitoring, create a script-only cron job (`no_agent=true`) that:

- lists readable channels,
- fetches recent `conversations.history`,
- stores per-channel last timestamps and a bounded seen-id set,
- prints nothing when there are no new messages,
- prints compact Markdown only for new messages,
- handles Slack 429s by honoring `Retry-After` once.

Deliver this to the user's preferred home thread. Once raw collection works, add a summarizing agent job on top for prioritization/action items.

## User-facing framing

When the user complains about low leverage, avoid setup-heavy tangents. Prioritize the systems they already use daily. For Slack monitoring, report clearly:

- workspace/bot authenticated,
- channels listable vs channels readable,
- what monitor was created,
- what access step remains (invite bot vs user OAuth),
- whether the job stays silent on no-op runs.
