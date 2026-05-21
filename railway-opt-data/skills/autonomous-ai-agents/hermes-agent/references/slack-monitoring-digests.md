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
- For DJ/Flow business briefings specifically, `SLACK_USER_TOKEN` must be DJ's user token (`xoxp-`, `auth.test` user `dj`, `bot_id: null`), not the bot token (`xoxb-`). A bot token may pass some tests but only covers bot-visible conversations.

## User-token scopes and MPIM verification

For company-wide/user-visible monitoring, verify scopes by testing the APIs rather than relying on Slack app UI alone:

```bash
/opt/hermes/.venv/bin/python - <<'PY'
import os, json, urllib.request, urllib.parse
# load SLACK_USER_TOKEN from env or /opt/data/.env before this snippet if needed

token = os.environ['SLACK_USER_TOKEN']
def api(method, params=None):
    data = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(
        'https://slack.com/api/' + method,
        data=data,
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/x-www-form-urlencoded'},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

print(json.dumps(api('auth.test'), indent=2))
print(json.dumps(api('conversations.list', {'types': 'mpim', 'limit': '1', 'exclude_archived': 'true'}), indent=2))
PY
```

Expected for DJ-level MPIM coverage:

- token prefix: `xoxp-`
- `auth.test.user == "dj"`
- `auth.test.bot_id` absent/null
- `conversations.list types=mpim` returns `ok: true`

If `conversations.list types=mpim` returns `missing_scope`, ensure `mpim:read` is under **User Token Scopes** (not only Bot Token Scopes), then re-authorize/reinstall the app or otherwise refresh the user token. Slack may keep the same visible token string while server-side scopes update, so re-check the API after a short delay instead of assuming a new token string is mandatory.

## Digest job pattern

For low-noise proactive monitoring, create a script-only cron job (`no_agent=true`) that:

- lists readable channels,
- fetches recent `conversations.history`,
- stores per-channel last timestamps and a bounded seen-id set,
- prints nothing when there are no new messages,
- prints compact Markdown only for new messages,
- handles Slack 429s by honoring `Retry-After` once.

Deliver this to the user's preferred home thread. Once raw collection works, add a summarizing agent job on top for prioritization/action items.

## Business briefing pipeline pattern

For high-volume Slack workspaces, do **not** send raw Slack dumps directly to Telegram and do **not** run an LLM over every workspace message. Use a two-job pipeline:

1. **Collection job** (`no_agent=true`, `deliver=local`): deterministic script only. Use `SLACK_USER_TOKEN`; collect broad Slack search hits, targeted terms, 1:1 DMs, and MPIM history; de-dupe by `channel:ts`; store state and write latest evidence to a local file such as `/opt/data/slack_business_brief_latest.md`.
2. **Briefing job** (`deliver=origin`): runs a few minutes later, with a small script/context bridge that prints the latest collection file plus rolling topic memory. The agent prompt filters aggressively and writes an executive brief with source links.
3. **Rolling topic memory**: maintain `/opt/data/slack_brief_archive/open_topics.md` plus dated final brief archives. Archive only curated brief outputs and open/watch topics, not raw Slack dumps. Use this rolling context to recognize continuations and say what changed since prior briefs.

For Eastern-time twice-daily briefs using UTC cron during EDT, schedule collection/briefing around:

- collection: `55 12,20 * * *` (8:55am / 4:55pm ET)
- briefing: `5 13,21 * * *` (9:05am / 5:05pm ET)

Keep both recurring jobs paused until the user explicitly approves enabling, especially when the workflow will consume LLM tokens. Test collection manually first and verify metadata such as DM and MPIM counts without dumping all raw Slack content back to the user.

For calibration/review, send draft briefs as editable Markdown files rather than long Telegram messages when the user needs to comment inline.

Implementation pitfalls:

- Slack search `after:YYYY-MM-DD` is date-oriented; query from the prior UTC date and enforce exact timestamp boundaries locally with Slack `ts` values.
- Slack search can miss or rank MPIMs oddly; explicitly crawl `conversations.list types=mpim` + `conversations.history` for group DMs when `mpim:read` works.
- A single Slack message is often insufficient for an executive brief. Before surfacing an item, collect surrounding thread/history context so the brief can say what happened, who said it, why it matters, and whether the user needs to act. Suppress low-context snippets instead of caveating that context is missing.
- Include source channel names next to Slack links, not just raw URLs.
- Do not promote items just because they match a keyword like MENA/finance/legal. Require either real blocker/decision/action context or meaningful business impact.
- Cap search pages, DM channels, history depth, and runtime so the script fits cron's hard execution limit.
- Filter channel list results by `is_im` / `is_mpim`; Slack may return surprising conversation IDs for broad requests.
- Preserve a bounded `seen` set and per-channel last timestamps (`im_last_ts`, `mpim_last_ts`) to prevent duplicate briefs.

## User-facing framing

When the user complains about low leverage, avoid setup-heavy tangents. Prioritize the systems they already use daily. For Slack monitoring, report clearly:

- workspace/bot authenticated,
- channels listable vs channels readable,
- what monitor was created,
- what access step remains (invite bot vs user OAuth),
- whether the job stays silent on no-op runs.
