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
import shutil
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

_INVISIBLE_RE = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff]')

DJ_ACTIVE_LOOKBACK_DAYS = int(os.getenv('SLACK_BRIEF_DJ_ACTIVE_LOOKBACK_DAYS', '7'))
MAX_ACTIVE_CHANNELS = int(os.getenv('SLACK_BRIEF_MAX_ACTIVE_CHANNELS', '80'))
MAX_HISTORY_PER_CHANNEL = int(os.getenv('SLACK_BRIEF_MAX_HISTORY_PER_CHANNEL', '20'))


def ensure_runtime_deps():
    """Re-exec under uv if slack_sdk is missing from the system Python.

    Cron currently launches this script directly. When the Slack SDK is absent
    from the base environment, we bootstrap a tiny ephemeral uv environment that
    includes the async Slack client plus aiohttp, then re-run the script there.
    """
    try:
        import slack_sdk  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    if os.environ.get('SLACK_BRIEF_COLLECT_BOOTSTRAPPED') == '1':
        raise
    if shutil.which('uv'):
        os.environ['SLACK_BRIEF_COLLECT_BOOTSTRAPPED'] = '1'
        os.execvp(
            'uv',
            [
                'uv',
                'run',
                '--with', 'slack-sdk',
                '--with', 'aiohttp',
                'python',
                __file__,
                *sys.argv[1:],
            ],
        )
    raise ModuleNotFoundError('slack_sdk is missing and uv is unavailable for bootstrap')

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

# Recent DM/MPIM refresh — a fresh short lookback for direct/group messages,
# independent of the broad last_ts watermark, so recent DMs are not missed
# when the broad workspace search advances last_ts with high-volume channel noise.
DM_REFRESH_LOOKBACK_HOURS = int(os.getenv('SLACK_BRIEF_DM_REFRESH_LOOKBACK_HOURS', '48'))

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
    text = _INVISIBLE_RE.sub('', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT - 1].rstrip() + '…'
    return text


def ts_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def is_dj_author(item, auth_names: set[str]) -> bool:
    author = re.sub(r'\s+', ' ', str(item.get('user') or '')).strip().lower()
    if not author or author == 'unknown':
        return False
    return author in auth_names


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


async def collect_search(client, query, seen, user_id, max_seen_ts, min_ts, include_seen: bool = False):
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
        if not ts or ((not include_seen) and key in seen) or (min_ts and msg_ts <= min_ts):
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
            if conv_kind == 'channel':
                item['active_dj_channel'] = True
                item['score'] += 120
                item['reasons'].append('recent DJ-active channel')
            items.append(item)
        last_by_channel[cid] = str(max_channel_ts or time.time())
    return items, max_seen_ts


async def main():
    ensure_runtime_deps()
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

    # Explicit DM/MPIM refresh: use a fixed recent lookback independent of
    # last_ts so direct/group messages are not missed when broad workspace search
    # has advanced last_ts with high-volume channel noise.
    dm_refresh_min_ts = max(0, now - DM_REFRESH_LOOKBACK_HOURS * 60 * 60)
    dm_refresh_date = (datetime.fromtimestamp(dm_refresh_min_ts, timezone.utc).date() - timedelta(days=1)).isoformat()
    for query in [f'is:dm after:{dm_refresh_date}', f'is:mpim after:{dm_refresh_date}']:
        try:
            items, total, max_seen_ts = await collect_search(
                client, query, seen, user_id, max_seen_ts, dm_refresh_min_ts, include_seen=True
            )
            totals[f'dm_refresh:{query.split()[0]}'] = total
            all_items.extend(items)
        except SlackApiError as e:
            totals[f'dm_refresh:{query.split()[0]}'] = f"error:{e.response.get('error')}"

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

    auth_names = {
        re.sub(r'\s+', ' ', str(x or '')).strip().lower()
        for x in [user_id, user_name, auth.get('real_name'), auth.get('team')]
        if re.sub(r'\s+', ' ', str(x or '')).strip().lower()
    }
    channel_last = state.get('channel_last_ts', {})
    active_channels = {}
    active_cutoff = max(0, now - DJ_ACTIVE_LOOKBACK_DAYS * 60 * 60 * 24)
    active_cutoff_date = (datetime.fromtimestamp(active_cutoff, timezone.utc).date() - timedelta(days=1)).isoformat()
    try:
        dj_query = f'from:me after:{active_cutoff_date}'
        dj_items, total, max_seen_ts = await collect_search(
            client, dj_query, set(), user_id, max_seen_ts, active_cutoff, include_seen=True
        )
        totals['dj_active'] = total
        for item in dj_items:
            if item.get('is_im') or item.get('is_mpim'):
                continue
            cid = item.get('channel_id')
            if cid and cid not in active_channels:
                active_channels[cid] = {'id': cid, 'name': item.get('channel') or cid}
    except SlackApiError as e:
        totals['dj_active'] = f"error:{e.response.get('error')}"

    if not active_channels:
        for item in all_items:
            if item.get('is_im') or item.get('is_mpim'):
                continue
            if is_dj_author(item, auth_names):
                cid = item.get('channel_id')
                if cid and cid not in active_channels:
                    active_channels[cid] = {'id': cid, 'name': item.get('channel') or cid}

    if active_channels:
        channel_last = state.get('channel_last_ts', {})
        active_convs = list(active_channels.values())[:MAX_ACTIVE_CHANNELS]
        try:
            items, mx = await collect_history(
                client,
                active_convs,
                'channel',
                channel_last,
                seen,
                user_id,
                active_cutoff,
                started_at,
            )
            all_items.extend(items)
            max_seen_ts = max(max_seen_ts, mx)
        except Exception:
            pass

    if active_channels:
        # Ensure each recently active DJ channel shows up even if the broad sweep
        # would otherwise crowd it out. This emits a single latest-message pulse.
        for cid, meta in list(active_channels.items())[:MAX_ACTIVE_CHANNELS]:
            try:
                hist = await slack_call_with_rate_limit(
                    client.conversations_history,
                    channel=cid,
                    oldest=str(active_cutoff),
                    limit=1,
                    inclusive=True,
                )
            except Exception:
                continue
            messages = hist.get('messages') or []
            if not messages:
                continue
            m = messages[0]
            ts = m.get('ts') or ''
            msg_ts = ts_float(ts)
            if not ts:
                continue
            text = clean_text(m.get('text'))
            if not text:
                continue
            item = {
                'source': 'channel_pulse',
                'ts': msg_ts,
                'raw_ts': ts,
                'thread_ts': m.get('thread_ts'),
                'time': fmt_time(msg_ts),
                'channel_id': cid,
                'channel': meta.get('name') or cid,
                'is_im': False,
                'is_mpim': False,
                'mentions_me': bool(user_id and f'<@{user_id}>' in (m.get('text') or '')),
                'user': m.get('user') or m.get('username') or 'unknown',
                'text': text,
                'permalink': f'https://slack.com/app_redirect?channel={cid}&message_ts={ts}',
                'active_dj_channel': True,
            }
            score_item(item)
            item['score'] += 120
            item['reasons'].append('recent DJ-active channel')
            all_items.append(item)

    if active_channels:
        active_ids = set(active_channels)
        for item in all_items:
            if item.get('is_im') or item.get('is_mpim'):
                continue
            if item.get('channel_id') in active_ids:
                item['active_dj_channel'] = True
                item['score'] += 120
                if 'recent DJ-active channel' not in item['reasons']:
                    item['reasons'].append('recent DJ-active channel')

    # Sort by score first, then recency; add thread/history context to high-signal
    # Sort by score first, then recency; add thread/history context to high-signal

    # candidates before capping so the LLM can suppress items that remain unclear.
    all_items.sort(key=lambda x: (x.get('score', 0), x.get('ts', 0)), reverse=True)
    unique_items = {}
    for item in all_items:
        key = f"{item.get('channel_id') or ''}:{item.get('raw_ts') or item.get('ts') or ''}"
        prev = unique_items.get(key)
        if prev is None:
            unique_items[key] = item
            continue
        prev_score = prev.get('score', 0)
        cur_score = item.get('score', 0)
        if item.get('source') == 'channel_pulse' or cur_score > prev_score:
            unique_items[key] = item
    ranked_items = sorted(unique_items.values(), key=lambda x: (x.get('score', 0), x.get('ts', 0)), reverse=True)
    user_cache = state.get('user_cache', {})
    await add_surrounding_context(client, ranked_items, user_cache)
    active_ranked = [item for item in ranked_items if item.get('active_dj_channel')]
    non_active_ranked = [item for item in ranked_items if not item.get('active_dj_channel')]
    active_quota = min(20, MAX_SEARCH_OUTPUT)
    output_items = active_ranked[:active_quota] + non_active_ranked[: max(0, MAX_SEARCH_OUTPUT - len(active_ranked[:active_quota]))]

    save_state({
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'last_ts': max_seen_ts or now,
        'seen': sorted(seen)[-20000:],
        'im_last_ts': im_last,
        'mpim_last_ts': mpim_last,
        'channel_last_ts': channel_last,
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
        if item.get('active_dj_channel'):
            markers.append('recent DJ-active channel')
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
