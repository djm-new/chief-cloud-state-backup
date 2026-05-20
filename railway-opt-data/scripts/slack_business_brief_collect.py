#!/usr/bin/env python3
"""Collect Slack candidates for DJ's business briefing.

No LLM is used here. The script reads Slack with DJ's SLACK_USER_TOKEN, gathers
workspace search hits plus direct/group-DM history, de-dupes by channel+ts, saves
state, and prints compact Markdown/JSON-ish evidence for a downstream Hermes
briefing job. Cron should usually deliver this locally and feed it to a separate
LLM synthesis job via context_from.
"""
import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ENV_PATH = Path('/opt/data/.env')
STATE_PATH = Path('/opt/data/slack_business_brief_collect_state.json')
OUTPUT_PATH = Path('/opt/data/slack_business_brief_latest.md')

MAX_SEARCH_SCAN = int(os.getenv('SLACK_BRIEF_MAX_SEARCH_SCAN', '200'))
MAX_SEARCH_OUTPUT = int(os.getenv('SLACK_BRIEF_MAX_SEARCH_OUTPUT', '120'))
# Keep defaults under cron's hard runtime limit. Search covers broad DM visibility;
# explicit history crawl is a safety net for recent/high-touch DMs and all small MPIM sets.
MAX_DM_CHANNELS = int(os.getenv('SLACK_BRIEF_MAX_DM_CHANNELS', '80'))
MAX_HISTORY_PER_DM = int(os.getenv('SLACK_BRIEF_MAX_HISTORY_PER_DM', '20'))
MAX_RUNTIME_SECONDS = int(os.getenv('SLACK_BRIEF_MAX_RUNTIME_SECONDS', '150'))
CONTEXT_LIMIT = int(os.getenv('SLACK_BRIEF_CONTEXT_LIMIT', '8'))
MAX_CONTEXT_ITEMS = int(os.getenv('SLACK_BRIEF_MAX_CONTEXT_ITEMS', '40'))
PAGE_SIZE = min(100, int(os.getenv('SLACK_BRIEF_SEARCH_PAGE_SIZE', '100')))
MAX_TEXT = int(os.getenv('SLACK_BRIEF_MAX_TEXT', '900'))
LOOKBACK_HOURS_FIRST_RUN = int(os.getenv('SLACK_BRIEF_FIRST_LOOKBACK_HOURS', '12'))

PRIORITY_TERMS = [
    'MENA', 'revenue', 'finance', 'blocker', 'blocked', 'urgent', 'customer',
    'churn', 'escalation', 'pricing', 'budget', 'cash', 'investor', 'board',
    'legal', 'compliance', 'hiring', 'roadmap', 'launch', 'incident', 'outage',
    'DJ', 'dj', '<@U05FS0SE77F>'
]

NOISE_SUBTYPES = {'channel_join', 'channel_leave', 'bot_message'}


def load_env():
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(errors='ignore').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        if k in {'SLACK_USER_TOKEN'} and k not in os.environ:
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


def fmt_time(ts):
    return datetime.fromtimestamp(float(ts), timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def score_item(item):
    text = (item.get('text') or '').lower()
    channel = (item.get('channel') or '').lower()
    score = 0
    reasons = []
    if item.get('mentions_me'):
        score += 100; reasons.append('mentions DJ')
    if item.get('is_mpim'):
        score += 70; reasons.append('group DM')
    elif item.get('is_im'):
        score += 65; reasons.append('direct DM')
    for term in PRIORITY_TERMS:
        t = term.lower()
        if t and (t in text or t in channel):
            score += 15; reasons.append(term)
    for marker in ['urgent', 'blocked', 'blocker', 'escalat', 'incident', 'outage', 'churn']:
        if marker in text:
            score += 20
    item['score'] = score
    item['reasons'] = sorted(set(reasons))[:8]
    return score


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


async def collect_search(client, query, seen, user_id, max_seen_ts, min_ts):
    matches = []
    total = None
    page = 1
    while len(matches) < MAX_SEARCH_SCAN:
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

    items = []
    for m in matches:
        ts = m.get('ts') or ''
        msg_ts = ts_float(ts)
        channel = m.get('channel') or {}
        cid = channel.get('id') or ''
        key = f'{cid}:{ts}'
        max_seen_ts = max(max_seen_ts, msg_ts)
        if not ts or key in seen or (min_ts and msg_ts <= min_ts):
            continue
        text = clean_text(m.get('text'))
        if not text:
            continue
        seen.add(key)
        item = {
            'source': 'search',
            'ts': msg_ts,
            'raw_ts': ts,
            'thread_ts': m.get('thread_ts'),
            'time': fmt_time(msg_ts),
            'channel_id': cid,
            'channel': channel.get('name') or cid or 'unknown',
            'is_im': bool(channel.get('is_im')),
            'is_mpim': bool(channel.get('is_mpim')),
            'mentions_me': bool(user_id and f'<@{user_id}>' in (m.get('text') or '')),
            'user': m.get('username') or m.get('user') or 'unknown',
            'text': text,
            'permalink': m.get('permalink') or '',
        }
        score_item(item)
        items.append(item)
    return items, total, max_seen_ts


async def resolve_user_name(client, user_id, cache):
    if not user_id or not str(user_id).startswith('U'):
        return user_id or 'unknown'
    if user_id in cache:
        return cache[user_id]
    try:
        resp = await slack_call_with_rate_limit(client.users_info, user=user_id)
        u = resp.get('user') or {}
        profile = u.get('profile') or {}
        name = profile.get('display_name') or profile.get('real_name') or u.get('real_name') or u.get('name') or user_id
    except Exception:
        name = user_id
    cache[user_id] = name
    return name


async def add_surrounding_context(client, items, user_cache):
    """Attach enough nearby Slack context that the briefing model can decide usefulness.

    For threads, fetch the thread. For standalone channel/DM messages, fetch several
    messages immediately before/including the item. If this fails, leave context empty;
    the briefing prompt is instructed to suppress low-context items.
    """
    from slack_sdk.errors import SlackApiError
    enriched = 0
    for item in items:
        if enriched >= MAX_CONTEXT_ITEMS:
            break
        if item.get('score', 0) <= 0 and not (item.get('is_im') or item.get('is_mpim')):
            continue
        cid = item.get('channel_id')
        ts = str(item.get('raw_ts') or item.get('ts') or '')
        if not cid or not ts:
            continue
        try:
            if item.get('thread_ts'):
                resp = await slack_call_with_rate_limit(
                    client.conversations_replies,
                    channel=cid,
                    ts=str(item['thread_ts']),
                    limit=CONTEXT_LIMIT,
                )
            else:
                resp = await slack_call_with_rate_limit(
                    client.conversations_history,
                    channel=cid,
                    latest=ts,
                    limit=CONTEXT_LIMIT,
                    inclusive=True,
                )
        except SlackApiError:
            continue
        except Exception:
            continue
        messages = resp.get('messages') or []
        messages = sorted(messages, key=lambda m: ts_float(m.get('ts')))
        context = []
        for m in messages[-CONTEXT_LIMIT:]:
            text = clean_text(m.get('text'))
            if not text:
                continue
            speaker = await resolve_user_name(client, m.get('user') or m.get('username') or m.get('bot_id'), user_cache)
            context.append({
                'time': fmt_time(ts_float(m.get('ts'))),
                'user': speaker,
                'text': text,
            })
        if context:
            item['context'] = context
            enriched += 1
    return items


async def list_conversations(client, types):
    channels = []
    cursor = None
    while True:
        resp = await slack_call_with_rate_limit(
            client.conversations_list,
            types=types,
            limit=200,
            cursor=cursor,
            exclude_archived=True,
        )
        batch = resp.get('channels', [])
        if types == 'mpim':
            batch = [c for c in batch if c.get('is_mpim')]
        elif types == 'im':
            batch = [c for c in batch if c.get('is_im')]
        channels.extend(batch)
        cursor = (resp.get('response_metadata') or {}).get('next_cursor')
        if not cursor:
            break
    return channels


async def collect_history(client, convs, conv_kind, last_by_channel, seen, user_id, fallback_oldest, started_at):
    from slack_sdk.errors import SlackApiError
    items = []
    max_seen_ts = 0.0
    for c in convs[:MAX_DM_CHANNELS]:
        if time.time() - started_at > MAX_RUNTIME_SECONDS:
            break
        cid = c.get('id') or ''
        if not cid or c.get('user') == 'USLACKBOT':
            continue
        oldest = str(last_by_channel.get(cid) or fallback_oldest)
        try:
            hist = await slack_call_with_rate_limit(
                client.conversations_history,
                channel=cid,
                oldest=oldest,
                limit=MAX_HISTORY_PER_DM,
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
            if not ts or key in seen or m.get('subtype') in NOISE_SUBTYPES:
                continue
            text = clean_text(m.get('text'))
            if not text:
                continue
            seen.add(key)
            item = {
                'source': conv_kind,
                'ts': msg_ts,
                'raw_ts': ts,
                'thread_ts': m.get('thread_ts'),
                'time': fmt_time(msg_ts),
                'channel_id': cid,
                'channel': c.get('name') or c.get('user') or cid,
                'is_im': conv_kind == 'im',
                'is_mpim': conv_kind == 'mpim',
                'mentions_me': bool(user_id and f'<@{user_id}>' in (m.get('text') or '')),
                'user': m.get('user') or m.get('username') or 'unknown',
                'text': text,
                'permalink': f'https://slack.com/app_redirect?channel={cid}&message_ts={ts}',
            }
            score_item(item)
            items.append(item)
        last_by_channel[cid] = str(max_channel_ts or time.time())
    return items, max_seen_ts


async def main():
    load_env()
    started_at = time.time()
    token = os.getenv('SLACK_USER_TOKEN')
    if not token:
        print('Slack business brief collector: SLACK_USER_TOKEN is not configured.')
        return

    from slack_sdk.web.async_client import AsyncWebClient
    from slack_sdk.errors import SlackApiError

    client = AsyncWebClient(token=token)
    try:
        auth = await client.auth_test()
    except Exception as e:
        print(f'Slack business brief collector: auth failed: {type(e).__name__}')
        return

    team = auth.get('team') or 'Slack'
    user_id = auth.get('user_id') or ''
    user_name = auth.get('user') or 'user'
    now = time.time()
    state = load_state()
    seen = set(state.get('seen', []))
    last_ts = ts_float(state.get('last_ts'))
    fallback_oldest = last_ts or max(0, now - LOOKBACK_HOURS_FIRST_RUN * 60 * 60)

    # Slack's `after:YYYY-MM-DD` is date-oriented, so query from the previous
    # UTC date and enforce the exact timestamp boundary locally.
    boundary_ts = last_ts or fallback_oldest
    start_date = (datetime.fromtimestamp(boundary_ts, timezone.utc).date() - timedelta(days=1)).isoformat()

    # Broad sweep + priority sweep. The broad query gives workspace pulse; priority query
    # pulls high-signal items into the first pages even if Slack search ranking is odd.
    priority_query = ' OR '.join([t for t in PRIORITY_TERMS if not t.startswith('<@')]) + f' after:{start_date}'
    broad_query = f'after:{start_date}'

    all_items = []
    totals = {}
    max_seen_ts = last_ts

    for label, query in [('broad', broad_query), ('priority', priority_query)]:
        try:
            items, total, max_seen_ts = await collect_search(client, query, seen, user_id, max_seen_ts, boundary_ts)
            totals[label] = total
            all_items.extend(items)
        except SlackApiError as e:
            totals[label] = f"error:{e.response.get('error')}"

    im_last = state.get('im_last_ts', {})
    mpim_last = state.get('mpim_last_ts', {})
    im_count = mpim_count = 0

    try:
        ims = await list_conversations(client, 'im')
        im_count = len(ims)
        items, mx = await collect_history(client, ims, 'im', im_last, seen, user_id, fallback_oldest, started_at)
        all_items.extend(items); max_seen_ts = max(max_seen_ts, mx)
    except Exception:
        pass

    mpim_error = None
    try:
        mpims = await list_conversations(client, 'mpim')
        mpim_count = len(mpims)
        items, mx = await collect_history(client, mpims, 'mpim', mpim_last, seen, user_id, fallback_oldest, started_at)
        all_items.extend(items); max_seen_ts = max(max_seen_ts, mx)
    except SlackApiError as e:
        mpim_error = e.response.get('error')
    except Exception as e:
        mpim_error = type(e).__name__

    # Sort by score first, then recency; add thread/history context to high-signal
    # candidates before capping so the LLM can suppress items that remain unclear.
    all_items.sort(key=lambda x: (x.get('score', 0), x.get('ts', 0)), reverse=True)
    user_cache = state.get('user_cache', {})
    await add_surrounding_context(client, all_items, user_cache)
    output_items = all_items[:MAX_SEARCH_OUTPUT]

    save_state({
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'last_ts': max_seen_ts or now,
        'seen': sorted(seen)[-20000:],
        'im_last_ts': im_last,
        'mpim_last_ts': mpim_last,
        'last_queries': {'broad': broad_query, 'priority': priority_query},
        'last_totals': totals,
        'im_count': im_count,
        'mpim_count': mpim_count,
        'mpim_error': mpim_error,
        'user_cache': user_cache,
    })

    if not output_items:
        # Write a small state file for debugging but keep stdout silent in normal no-op runs.
        OUTPUT_PATH.write_text(f'No new Slack business-brief candidates at {datetime.now(timezone.utc).isoformat()}\n')
        return

    lines = []
    lines.append(f'# Slack Business Brief Collection — {team} as {user_name}')
    lines.append(f'Collected at: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')
    lines.append(f'Window start date: {start_date}; broad total: {totals.get("broad")}; priority total: {totals.get("priority")}')
    lines.append(f'DM conversations scanned: {im_count}; group DMs scanned: {mpim_count}; group DM error: {mpim_error or "none"}')
    lines.append(f'Candidate items emitted: {len(output_items)} of {len(all_items)} new collected')
    lines.append('')
    lines.append('## Candidate Slack items')
    for i, item in enumerate(output_items, 1):
        markers = []
        if item.get('is_mpim'):
            markers.append('group DM')
        elif item.get('is_im'):
            markers.append('DM')
        if item.get('mentions_me'):
            markers.append('mentions DJ')
        if item.get('reasons'):
            markers.append('signals: ' + ', '.join(item['reasons'][:5]))
        marker = f" ({'; '.join(markers)})" if markers else ''
        lines.append(f'{i}. [{item["time"]}] #{item["channel"]}{marker} — {item["user"]}')
        lines.append(f'   Score: {item.get("score", 0)}')
        lines.append(f'   Text: {item["text"]}')
        if item.get('permalink'):
            lines.append(f'   Source: #{item["channel"]} — {item["permalink"]}')
        if item.get('context'):
            lines.append('   Context:')
            for ctx in item['context']:
                lines.append(f'   - [{ctx["time"]}] {ctx["user"]}: {ctx["text"]}')
    output = '\n'.join(lines) + '\n'
    OUTPUT_PATH.write_text(output)
    print(output)


if __name__ == '__main__':
    asyncio.run(main())
