#!/usr/bin/env python3
"""Track DJ-authored Slack messages for 48h and 1-week follow-up checks.

This is deterministic context for the smart business briefing, not a notifier.
It records DJ's own Slack messages, then at ~48h and ~7d fetches nearby/thread
activity so the briefing model can decide whether the item landed or still needs
follow-up. It stays compact: stdout includes counts plus due/open traces only.
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

ENV_PATH = Path('/opt/data/.env')
STATE_PATH = Path('/opt/data/slack_dj_followup_trace_state.json')
OUTPUT_PATH = Path('/opt/data/slack_dj_followup_trace.md')

LOOKBACK_DAYS = int(os.getenv('SLACK_DJ_TRACE_LOOKBACK_DAYS', '10'))
MAX_SEARCH_SCAN = int(os.getenv('SLACK_DJ_TRACE_MAX_SEARCH_SCAN', '500'))
PAGE_SIZE = min(100, int(os.getenv('SLACK_DJ_TRACE_PAGE_SIZE', '100')))
MAX_DUE_OUTPUT = int(os.getenv('SLACK_DJ_TRACE_MAX_DUE_OUTPUT', '25'))
CONTEXT_LIMIT = int(os.getenv('SLACK_DJ_TRACE_CONTEXT_LIMIT', '12'))
MAX_TEXT = int(os.getenv('SLACK_DJ_TRACE_MAX_TEXT', '700'))
# Allow small slack around exact due time so a briefing run catches items soon after checkpoint.
DUE_GRACE_SECONDS = int(os.getenv('SLACK_DJ_TRACE_DUE_GRACE_SECONDS', str(60 * 60)))

CHECKPOINTS = {
    '48h': 48 * 60 * 60,
    '1w': 7 * 24 * 60 * 60,
}

_INVISIBLE_RE = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff]')
ACTION_WORDS = re.compile(
    r'\b(please|pls|can you|could you|need|needs|should|must|confirm|send|share|review|approve|follow up|circle back|own|owner|date|deadline|when|eta|block|blocked|unblock|decide|decision|align|close|land|make sure)\b',
    re.I,
)
LANDING_WORDS = re.compile(
    r'\b(done|completed|resolved|shipped|sent|shared|closed|landed|approved|saved|uploaded|posted|confirmed|confirming|clear definition|yep|yes|will do|on it)\b',
    re.I,
)


def ensure_runtime_deps():
    try:
        import slack_sdk  # noqa: F401
        return
    except ModuleNotFoundError:
        pass
    if os.environ.get('SLACK_DJ_TRACE_BOOTSTRAPPED') == '1':
        raise
    if shutil.which('uv'):
        os.environ['SLACK_DJ_TRACE_BOOTSTRAPPED'] = '1'
        os.execvp('uv', ['uv', 'run', '--with', 'slack-sdk', '--with', 'aiohttp', 'python', __file__, *sys.argv[1:]])
    raise ModuleNotFoundError('slack_sdk is missing and uv is unavailable')


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
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding='utf-8')
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


def fmt_time(ts):
    return datetime.fromtimestamp(float(ts), timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def date_for_query(ts):
    return (datetime.fromtimestamp(ts, timezone.utc).date() - timedelta(days=1)).isoformat()


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


async def collect_dj_messages(client, since_ts):
    start_date = date_for_query(since_ts)
    query = f'from:me after:{start_date}'
    matches = []
    page = 1
    total = None
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

    out = []
    for m in matches:
        msg_ts = ts_float(m.get('ts'))
        if msg_ts < since_ts:
            continue
        channel = m.get('channel') or {}
        cid = channel.get('id') or ''
        text = clean_text(m.get('text'))
        if not cid or not msg_ts or not text:
            continue
        out.append({
            'key': f'{cid}:{m.get("ts")}',
            'ts': msg_ts,
            'raw_ts': m.get('ts'),
            'thread_ts': m.get('thread_ts'),
            'channel_id': cid,
            'channel': channel.get('name') or cid,
            'is_im': bool(channel.get('is_im')),
            'is_mpim': bool(channel.get('is_mpim')),
            'text': text,
            'permalink': m.get('permalink') or f'https://slack.com/app_redirect?channel={cid}&message_ts={m.get("ts")}',
            'actionish': bool(ACTION_WORDS.search(text)),
        })
    return out, total


async def fetch_follow_context(client, item, user_cache, dj_user_id):
    cid = item.get('channel_id')
    raw_ts = str(item.get('raw_ts') or item.get('ts') or '')
    thread_ts = str(item.get('thread_ts') or raw_ts)
    if not cid or not raw_ts:
        return [], False
    try:
        if item.get('thread_ts'):
            resp = await slack_call_with_rate_limit(client.conversations_replies, channel=cid, ts=thread_ts, limit=CONTEXT_LIMIT)
            messages = resp.get('messages') or []
        else:
            # For non-threaded messages, fetch immediately after the DJ message through now.
            resp = await slack_call_with_rate_limit(client.conversations_history, channel=cid, oldest=raw_ts, limit=CONTEXT_LIMIT, inclusive=False)
            messages = list(reversed(resp.get('messages') or []))
    except Exception:
        return [], False

    context = []
    non_dj_response = False
    for m in messages:
        msg_ts = ts_float(m.get('ts'))
        if msg_ts <= ts_float(raw_ts):
            continue
        text = clean_text(m.get('text'))
        if not text:
            continue
        uid = m.get('user') or m.get('username') or m.get('bot_id')
        if dj_user_id and uid and uid != dj_user_id:
            non_dj_response = True
        speaker = await resolve_user_name(client, uid, user_cache)
        context.append({'time': fmt_time(msg_ts), 'user': speaker, 'text': text})
    return context[-CONTEXT_LIMIT:], non_dj_response


def outcome_label(context, non_dj_response):
    if not context:
        return 'no visible follow-up yet'
    blob = ' '.join(x['text'] for x in context).lower()
    if LANDING_WORDS.search(blob):
        return 'likely landed / suppress unless newly contradicted'
    if non_dj_response:
        return 'response exists / verify landed'
    return 'DJ follow-up only / still unclear'


async def main():
    ensure_runtime_deps()
    load_env()
    token = os.getenv('SLACK_USER_TOKEN')
    if not token:
        OUTPUT_PATH.write_text('Slack DJ follow-up trace: SLACK_USER_TOKEN is not configured.\n')
        print(OUTPUT_PATH.read_text())
        return

    from slack_sdk.web.async_client import AsyncWebClient
    from slack_sdk.errors import SlackApiError

    client = AsyncWebClient(token=token)
    try:
        auth = await client.auth_test()
    except Exception as e:
        text = f'Slack DJ follow-up trace: auth failed: {type(e).__name__}\n'
        OUTPUT_PATH.write_text(text)
        print(text)
        return

    now = time.time()
    since_ts = now - LOOKBACK_DAYS * 24 * 60 * 60
    state = load_state()
    tracked = state.get('tracked', {})
    user_cache = state.get('user_cache', {})
    dj_user_id = auth.get('user_id') or ''

    try:
        dj_items, search_total = await collect_dj_messages(client, since_ts)
    except SlackApiError as e:
        text = f'Slack DJ follow-up trace: search failed: {e.response.get("error")}\n'
        OUTPUT_PATH.write_text(text)
        print(text)
        return

    for item in dj_items:
        rec = tracked.get(item['key'], {})
        rec.update({
            'key': item['key'],
            'ts': item['ts'],
            'raw_ts': item['raw_ts'],
            'thread_ts': item.get('thread_ts'),
            'channel_id': item['channel_id'],
            'channel': item['channel'],
            'is_im': item['is_im'],
            'is_mpim': item['is_mpim'],
            'text': item['text'],
            'permalink': item['permalink'],
            'actionish': item['actionish'],
        })
        rec.setdefault('checks', {})
        tracked[item['key']] = rec

    # Prune old records after the 1-week check has had time to be seen in a few briefings.
    prune_before = now - (LOOKBACK_DAYS + 2) * 24 * 60 * 60
    tracked = {k: v for k, v in tracked.items() if ts_float(v.get('ts')) >= prune_before}

    due = []
    for rec in tracked.values():
        age = now - ts_float(rec.get('ts'))
        rec_due = []
        for label, seconds in CHECKPOINTS.items():
            if age + DUE_GRACE_SECONDS >= seconds and not rec.get('checks', {}).get(label, {}).get('checked_at'):
                rec_due.append((seconds, label))
        # If both checkpoints are overdue on a first/backfill run, process only the latest due checkpoint.
        if rec_due:
            _, label = sorted(rec_due)[-1]
            due.append((ts_float(rec.get('ts')), label, rec))
    due.sort(key=lambda x: (x[0], x[1]))

    lines = []
    lines.append('# DJ Slack Follow-up Trace')
    lines.append(f'Collected at: {fmt_time(now)}')
    lines.append(f'DJ-authored messages tracked in last {LOOKBACK_DAYS}d: {len(tracked)}; Slack search total: {search_total}')
    lines.append('Policy: every DJ-authored Slack message is checkpointed at ~48h and ~1w. The briefing should surface only unclear/high-importance traces, not all records.')
    lines.append('')

    lines.append('## Due trace checks')
    if not due:
        lines.append('No DJ-authored Slack messages are due for 48h/1w follow-up checks right now.')
    else:
        surfaced = 0
        checked = 0
        suppressed = 0
        # Check all due items, but surface only items that might need attention.
        for _, label, rec in due:
            context, non_dj_response = await fetch_follow_context(client, rec, user_cache, dj_user_id)
            result = outcome_label(context, non_dj_response)
            rec.setdefault('checks', {})[label] = {
                'checked_at': datetime.now(timezone.utc).isoformat(),
                'result': result,
                'context_count': len(context),
                'non_dj_response': non_dj_response,
            }
            checked += 1
            should_surface = bool(rec.get('actionish')) and not result.startswith('likely landed')
            if not should_surface:
                suppressed += 1
                continue
            if surfaced >= MAX_DUE_OUTPUT:
                suppressed += 1
                continue
            importance = 'action-like' if rec.get('actionish') else 'general'
            dest = 'DM/MPIM' if rec.get('is_im') or rec.get('is_mpim') else f"#{rec.get('channel')}"
            lines.append(f'- **{label} check — {dest} — {importance} — {result}**')
            lines.append(f'  - DJ sent [{fmt_time(rec.get("ts"))}]: {rec.get("text")}')
            if rec.get('permalink'):
                lines.append(f'  - Source: {rec.get("permalink")}')
            if context:
                lines.append('  - Follow-up context:')
                for ctx in context[-5:]:
                    lines.append(f'    - [{ctx["time"]}] {ctx["user"]}: {ctx["text"]}')
            else:
                lines.append('  - Follow-up context: no visible reply/context found after DJ message.')
            surfaced += 1
        if surfaced == 0:
            lines.append(f'{checked} due checks processed; none need to be surfaced in the briefing.')
        elif suppressed:
            lines.append(f'\nSuppressed from briefing context: {suppressed} tracked messages that appear landed/non-actionable.')

    save_state({
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'tracked': tracked,
        'user_cache': user_cache,
    })
    output = '\n'.join(lines) + '\n'
    OUTPUT_PATH.write_text(output, encoding='utf-8')
    print(output)


if __name__ == '__main__':
    asyncio.run(main())
