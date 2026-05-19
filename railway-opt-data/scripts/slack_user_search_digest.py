#!/usr/bin/env python3
"""Twice-daily Slack digest using a user token and Slack search.

This avoids per-channel polling. With SLACK_USER_TOKEN + search:read, one paginated
search sees messages accessible to the user across public/private channels and DMs.
Prints nothing when no new matches are found so no_agent cron stays silent.
"""
import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ENV_PATH = Path('/opt/data/.env')
STATE_PATH = Path('/opt/data/slack_user_search_digest_state.json')
MAX_MATCHES_SCAN = int(os.getenv('SLACK_DIGEST_MAX_SEARCH_SCAN', '500'))
MAX_MATCHES_OUTPUT = int(os.getenv('SLACK_DIGEST_MAX_SEARCH_OUTPUT', '120'))
PAGE_SIZE = min(100, int(os.getenv('SLACK_DIGEST_SEARCH_PAGE_SIZE', '100')))
MAX_TEXT = int(os.getenv('SLACK_DIGEST_MAX_TEXT', '700'))


def load_env():
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(errors='ignore').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        if k == 'SLACK_USER_TOKEN' and k not in os.environ:
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


def ts_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


async def slack_call_with_rate_limit(fn, **kwargs):
    from slack_sdk.errors import SlackApiError
    try:
        return await fn(**kwargs)
    except SlackApiError as e:
        if e.response.get('error') == 'ratelimited':
            retry_after = int(e.response.headers.get('Retry-After', '30'))
            await asyncio.sleep(min(retry_after, 60))
            return await fn(**kwargs)
        raise


async def main():
    load_env()
    token = os.getenv('SLACK_USER_TOKEN')
    if not token:
        print('Slack digest: SLACK_USER_TOKEN is not configured in this runtime.')
        return

    from slack_sdk.web.async_client import AsyncWebClient
    from slack_sdk.errors import SlackApiError

    client = AsyncWebClient(token=token)
    try:
        auth = await client.auth_test()
    except Exception as e:
        print(f'Slack digest: user-token auth failed: {type(e).__name__}')
        return

    team = auth.get('team') or 'Slack'
    user_id = auth.get('user_id') or ''
    user_name = auth.get('user') or 'user'

    state = load_state()
    seen = set(state.get('seen', []))
    last_ts = float(state.get('last_ts') or 0)

    # Search supports date operators but not robust timestamp operators. Query since the
    # previous run's UTC date (or yesterday on first run) and de-dupe/filter by ts locally.
    if last_ts:
        start_date = datetime.fromtimestamp(last_ts, timezone.utc).date().isoformat()
    else:
        start_date = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    query = f'after:{start_date}'

    matches = []
    total = None
    page = 1
    try:
        while len(matches) < MAX_MATCHES_SCAN:
            resp = await slack_call_with_rate_limit(
                client.search_messages,
                query=query,
                count=PAGE_SIZE,
                page=page,
                sort='timestamp',
                sort_dir='desc',
            )
            messages = resp.get('messages') or {}
            if total is None:
                total = messages.get('total')
            batch = messages.get('matches') or []
            if not batch:
                break
            matches.extend(batch)
            paging = messages.get('paging') or {}
            pages = int(paging.get('pages') or page)
            if page >= pages:
                break
            page += 1
    except SlackApiError as e:
        print(f"Slack digest: search failed: {e.response.get('error')} needed={e.response.get('needed')}")
        return
    except Exception as e:
        print(f'Slack digest: search failed: {type(e).__name__}')
        return

    new_items = []
    max_seen_ts = last_ts
    for m in matches:
        ts = m.get('ts') or ''
        channel = m.get('channel') or {}
        cid = channel.get('id') or ''
        key = f'{cid}:{ts}'
        msg_ts = ts_float(ts)
        max_seen_ts = max(max_seen_ts, msg_ts)
        if key in seen or (last_ts and msg_ts <= last_ts):
            continue
        text = clean_text(m.get('text'))
        if not text:
            continue
        seen.add(key)
        channel_name = channel.get('name') or cid or 'unknown'
        is_dm = bool(channel.get('is_im') or channel.get('is_mpim'))
        mentions_me = bool(user_id and f'<@{user_id}>' in (m.get('text') or ''))
        new_items.append({
            'ts': msg_ts,
            'time': datetime.fromtimestamp(msg_ts, timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
            'channel': channel_name,
            'is_dm': is_dm,
            'is_mpim': bool(channel.get('is_mpim')),
            'mentions_me': mentions_me,
            'user': m.get('username') or m.get('user') or 'unknown',
            'text': text,
            'permalink': m.get('permalink') or '',
        })

    # Slack search can be spotty for multi-person DMs, so explicitly crawl MPIMs
    # when the user token has mpim:read. If the scope is absent, skip quietly.
    mpim_last = state.get('mpim_last_ts', {})
    mpim_count = 0
    try:
        cursor = None
        mpims = []
        while True:
            resp = await slack_call_with_rate_limit(
                client.conversations_list,
                types='mpim',
                limit=200,
                cursor=cursor,
                exclude_archived=True,
            )
            mpims.extend(resp.get('channels', []))
            cursor = (resp.get('response_metadata') or {}).get('next_cursor')
            if not cursor:
                break
        mpim_count = len(mpims)
        for c in mpims:
            cid = c.get('id') or ''
            if not cid:
                continue
            oldest = str(mpim_last.get(cid) or last_ts or max(0, time.time() - 12 * 60 * 60))
            try:
                hist = await slack_call_with_rate_limit(
                    client.conversations_history,
                    channel=cid,
                    oldest=oldest,
                    limit=50,
                    inclusive=False,
                )
            except SlackApiError:
                continue
            max_channel_ts = ts_float(oldest)
            for m in reversed(hist.get('messages', [])):
                ts = m.get('ts') or ''
                msg_ts = ts_float(ts)
                max_channel_ts = max(max_channel_ts, msg_ts)
                max_seen_ts = max(max_seen_ts, msg_ts)
                key = f'{cid}:{ts}'
                if not ts or key in seen:
                    continue
                if m.get('subtype') in {'channel_join', 'channel_leave', 'bot_message'}:
                    continue
                text = clean_text(m.get('text'))
                if not text:
                    continue
                seen.add(key)
                mentions_me = bool(user_id and f'<@{user_id}>' in (m.get('text') or ''))
                channel_name = c.get('name') or cid
                new_items.append({
                    'ts': msg_ts,
                    'time': datetime.fromtimestamp(msg_ts, timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                    'channel': channel_name,
                    'is_dm': True,
                    'is_mpim': True,
                    'mentions_me': mentions_me,
                    'user': m.get('user') or m.get('username') or 'unknown',
                    'text': text,
                    'permalink': f'https://slack.com/app_redirect?channel={cid}&message_ts={ts}',
                })
            mpim_last[cid] = str(max_channel_ts or time.time())
    except SlackApiError as e:
        if e.response.get('error') != 'missing_scope':
            print(f"Slack digest: MPIM crawl failed: {e.response.get('error')}")
    except Exception as e:
        print(f'Slack digest: MPIM crawl failed: {type(e).__name__}')

    save_state({
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'last_ts': max_seen_ts or time.time(),
        'seen': sorted(seen)[-10000:],
        'last_query': query,
        'last_total': total,
        'mpim_last_ts': mpim_last,
        'mpim_count': mpim_count,
    })

    if not new_items:
        return

    new_items.sort(key=lambda x: x['ts'], reverse=True)
    priority = [x for x in new_items if x['is_dm'] or x['mentions_me']]
    rest = [x for x in new_items if x not in priority]
    output_items = (priority + rest)[:MAX_MATCHES_OUTPUT]

    print(f'🔎 Slack twice-daily digest — {team} as {user_name}')
    print(f'Query: {query}; search total visible: {total}; new captured: {len(new_items)}')
    if priority:
        print(f'Priority items (DMs / mentions): {len(priority)}')
    if len(new_items) > len(output_items):
        print(f'Note: showing {len(output_items)} newest/priority items; {len(new_items) - len(output_items)} additional new matches omitted.')
    print('')
    for item in output_items:
        markers = []
        if item.get('is_mpim'):
            markers.append('group DM')
        elif item['is_dm']:
            markers.append('DM')
        if item['mentions_me']:
            markers.append('mentions you')
        marker = f" ({', '.join(markers)})" if markers else ''
        print(f"- [{item['time']}] #{item['channel']}{marker} — {item['user']}: {item['text']}")
        if item['permalink']:
            print(f"  {item['permalink']}")


if __name__ == '__main__':
    asyncio.run(main())
