#!/usr/bin/env python3
"""Collect new Slack messages from channels the Hermes Slack bot can read.

Loads SLACK_BOT_TOKEN from /opt/data/.env without printing it, lists channels the bot is
a member of, fetches recent history, de-duplicates by channel+ts, and prints compact
Markdown for a Hermes cron summarizer.
"""
import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path('/opt/data/slack_monitor_state.json')
ENV_PATH = Path('/opt/data/.env')
MAX_CHANNELS = int(os.getenv('SLACK_DIGEST_MAX_CHANNELS', '200'))
MAX_MESSAGES_PER_CHANNEL = int(os.getenv('SLACK_DIGEST_MAX_MESSAGES_PER_CHANNEL', '50'))
MAX_TEXT = int(os.getenv('SLACK_DIGEST_MAX_TEXT', '1000'))
LOOKBACK_SECONDS = int(os.getenv('SLACK_DIGEST_LOOKBACK_SECONDS', str(60 * 60)))


def load_env():
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(errors='ignore').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        if k in {'SLACK_USER_TOKEN', 'SLACK_BOT_TOKEN'} and k not in os.environ:
            os.environ[k] = v.strip().strip('"').strip("'")


def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            return {}
    return {}


def save_state(state):
    tmp = STATE_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(STATE_PATH)


def clean_text(text):
    text = re.sub(r'\s+', ' ', text or '').strip()
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT - 1].rstrip() + '…'
    return text


async def slack_call_with_rate_limit(fn, **kwargs):
    """Call Slack API, waiting once if Slack returns a Retry-After rate limit."""
    from slack_sdk.errors import SlackApiError
    try:
        return await fn(**kwargs)
    except SlackApiError as e:
        if e.response.get('error') == 'ratelimited':
            retry_after = int(e.response.headers.get('Retry-After', '30'))
            await asyncio.sleep(min(retry_after, 60))
            return await fn(**kwargs)
        raise


async def list_readable_candidate_channels(client, include_all_listed=False):
    channels = []
    cursor = None
    while True:
        resp = await slack_call_with_rate_limit(
            client.conversations_list,
            types='public_channel,private_channel,mpim,im',
            limit=200,
            cursor=cursor,
            exclude_archived=True,
        )
        for c in resp.get('channels', []):
            # conversations.history only works where the bot is a member; DMs/MPIMs may not expose is_member.
            # Skip Slackbot/system DMs that commonly list but return channel_not_found.
            if c.get('user') == 'USLACKBOT':
                continue
            if include_all_listed or c.get('is_member') or c.get('is_im') or c.get('is_mpim') or str(c.get('id','')).startswith(('D','G')):
                channels.append(c)
        cursor = (resp.get('response_metadata') or {}).get('next_cursor')
        if not cursor:
            break
    return channels[:MAX_CHANNELS]


async def main():
    load_env()
    token = os.getenv('SLACK_USER_TOKEN') or os.getenv('SLACK_BOT_TOKEN')
    token_kind = 'user' if os.getenv('SLACK_USER_TOKEN') else 'bot'
    if not token:
        print('Slack digest: neither SLACK_USER_TOKEN nor SLACK_BOT_TOKEN is configured.')
        return

    from slack_sdk.web.async_client import AsyncWebClient
    from slack_sdk.errors import SlackApiError

    client = AsyncWebClient(token=token)
    now = time.time()
    state = load_state()
    seen = set(state.get('seen', []))
    channel_last = state.get('channel_last_ts', {})

    try:
        auth = await client.auth_test()
        team = auth.get('team') or 'Slack'
    except Exception as e:
        print(f'Slack digest: auth failed: {type(e).__name__}')
        return

    try:
        channels = await list_readable_candidate_channels(client, include_all_listed=(token_kind == 'user'))
    except Exception as e:
        print(f'Slack digest: channel listing failed: {type(e).__name__}')
        return

    collected = []
    errors = []
    oldest_default = str(max(0, now - LOOKBACK_SECONDS))

    for c in channels:
        cid = c.get('id')
        name = c.get('name') or c.get('user') or cid
        oldest = channel_last.get(cid) or oldest_default
        try:
            resp = await slack_call_with_rate_limit(
                client.conversations_history,
                channel=cid,
                oldest=str(oldest),
                limit=MAX_MESSAGES_PER_CHANNEL,
                inclusive=False,
            )
        except SlackApiError as e:
            errors.append(f"#{name}: {e.response.get('error', 'api_error')}")
            continue
        except Exception as e:
            errors.append(f"#{name}: {type(e).__name__}")
            continue

        max_ts = float(oldest) if str(oldest).replace('.','',1).isdigit() else 0.0
        for m in reversed(resp.get('messages', [])):
            ts = m.get('ts')
            if not ts:
                continue
            max_ts = max(max_ts, float(ts))
            key = f'{cid}:{ts}'
            if key in seen:
                continue
            # Skip bot/system noise by default, but include app/user messages with text.
            if m.get('subtype') in {'channel_join', 'channel_leave', 'bot_message'}:
                continue
            text = clean_text(m.get('text'))
            if not text:
                continue
            seen.add(key)
            dt = datetime.fromtimestamp(float(ts), timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            user = m.get('user') or m.get('username') or m.get('bot_id') or 'unknown'
            thread = m.get('thread_ts') and m.get('thread_ts') != ts
            collected.append({
                'channel': name,
                'channel_id': cid,
                'ts': ts,
                'time': dt,
                'user': user,
                'thread_reply': bool(thread),
                'text': text,
                'url_hint': f'https://slack.com/app_redirect?channel={cid}&message_ts={ts}',
            })
        channel_last[cid] = str(max_ts if max_ts else now)

    # Bound de-dupe state.
    recent_seen = sorted(seen)[-5000:]
    save_state({
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'seen': recent_seen,
        'channel_last_ts': channel_last,
        'channels_monitored': [{'id': c.get('id'), 'name': c.get('name') or c.get('user') or c.get('id')} for c in channels],
    })

    if not collected:
        # Silent on normal no-op runs; cron no_agent jobs deliver nothing on empty stdout.
        if errors:
            print(f'Slack digest source: {team} ({token_kind} token)')
            print(f'Readable channels monitored: {len(channels)}')
            print('Fetch warnings: ' + '; '.join(errors[:10]))
        return

    print(f'🔎 Slack digest — {team} ({token_kind} token)')
    print(f'Readable channels monitored: {len(channels)}')
    if errors:
        print('Fetch warnings: ' + '; '.join(errors[:10]))
    print(f'New messages: {len(collected)}')
    for item in collected[-200:]:
        thread = ' thread-reply' if item['thread_reply'] else ''
        print(f"- [{item['time']}] #{item['channel']} <@{item['user']}>{thread}: {item['text']}")
        print(f"  Link: {item['url_hint']}")


if __name__ == '__main__':
    asyncio.run(main())
