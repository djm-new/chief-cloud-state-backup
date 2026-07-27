#!/usr/bin/env python3
"""Executive-relevance filter for Slack crawl evidence before LLM briefing.

Input: /opt/data/slack_business_brief_latest.md
Output: filtered Markdown to stdout.

DJ calibration rules (v3 — 2026-05-27):
- DMs/MPIMs/mentions: always surface. Must include enough context for the briefing to interpret.
- Exact Daily ToM entities: surface even when channel chatter is otherwise weak.
- Priority channels (deal/acquisition/MENA): always surface relevant content.
- Tour/prospect feedback in leasing channels: useful signal — include.
- Engineering notable items with named entities or product decisions: include.
- Conductor / Slackbot app install requests: hard-exclude — IT's job, not DJ.
- Generic bot test/status noise: hard-exclude.
- Renewal admin chatter with no tour/prospect/money/legal signal: exclude.
- Low-context ops messages (Break, Listo, etc.): exclude.
Read-only.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

LATEST = Path('/opt/data/slack_business_brief_latest.md')
MAX_ITEMS = 22
MAX_ITEMS_CHANNEL_PULSE = 15   # additional lower-score items for business pulse
MAX_CONTEXT_LINES_PER_ITEM = 8   # Increased — DMs need more context to interpret
MAX_TEXT_LEN = 750

# Exact/high-value entities from DJ's active ToM.
TOM_ENTITIES = [
    'easton', 'wynwood', 'flow wynwood', 'society wynwood', 'mena', 'sico', 'olaya',
    'hubspot', 'f&b', 'mbr', 'board deck', 'flow overview', 'xm comp',
    'interview tool', 'granola', 'evernote', 'experian', 'vp safe',
]

# Signals that usually justify executive awareness.
EXEC_SIGNALS = [
    'approve', 'approval', 'decision', 'urgent', 'asap', 'blocked', 'blocker', 'stuck',
    'escalat', 'deadline', 'today', 'tomorrow', 'contract', 'legal', 'signature',
    'wire', 'payment', 'invoice', 'drawdown', 'capital', '$', 'revenue', 'budget',
    'cash', 'pricing', 'churn', 'customer escalation', 'board', 'investor', 'dd ',
    'due diligence', 'data room', 'access agreement', 'loan',
    'security', 'permission', 'degraded', 'outage', 'incident',
]

# Tour/prospect signals in leasing channels — valuable to DJ.
LEASING_SIGNALS = [
    'tour', 'tours', 'prospect', 'prospective', 'showing', 'walkthrough', 'walk-through',
    'walk through', 'visitor', 'occupancy', 'vacancy', 'vacant', 'traffic',
    'conversion', 'move-in', 'move in', 'available unit', 'waiting', 'wait',
    'no one here', 'nobody here', 'people waiting',
]

# Channels about key deals/projects — always relevant context if they have substance.
PRIORITY_CHANNELS = {
    'proj-society-wynwood-acquisition', 'proj-mena', 'proj-easton',
    'proj-flow-mena', 'mena', 'easton',
}

# Pure noise — hard exclusions regardless of other signals.
NOISE_CHANNELS = {'plattest-012n3', 'test-android-results', 'waves-dev-test-automation',
                  'backend-dev-testify-automation', 'application-status'}
BOT_USERS = {'platformsbot', 'flow pr bot', 'test automation', 'rootly', 'uslackbot'}
CLEANING_CHANNELS = re.compile(r'(cleaning|housekeeping)', re.I)

ITEM_RE = re.compile(r"^(?P<num>\d+)\. \[(?P<time>[^\]]+)\] #(?P<channel>[^\s(]+)(?P<markers>.*?) — (?P<user>.+)$")
SCORE_RE = re.compile(r"^\s*Score:\s*(?P<score>-?\d+)")
TEXT_RE = re.compile(r"^\s*Text:\s*(?P<text>.*)$")
SOURCE_RE = re.compile(r"^\s*Source:\s*(?P<src>.*)$")
_INVISIBLE_RE = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff]')

LEASING_CHANNELS = re.compile(r'(leasing|renewals|brickell|mia-west|mia-east|waves-leasing|fx-leasing)', re.I)


def truncate(s: str, n: int = MAX_TEXT_LEN) -> str:
    s = _INVISIBLE_RE.sub('', s or '')
    s = re.sub(r'\s+', ' ', s).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + '…'


def parse(md: str):
    md = _INVISIBLE_RE.sub('', md or '')
    header, items, cur, in_items = [], [], None, False
    for line in md.splitlines():
        m = ITEM_RE.match(line)
        if m:
            in_items = True
            if cur:
                items.append(cur)
            cur = {'head': line, 'score': 0, 'text': '', 'source': '', 'context': [], **m.groupdict()}
            continue
        if not in_items:
            header.append(line)
            continue
        if cur is None:
            continue
        sm = SCORE_RE.match(line)
        if sm:
            cur['score'] = int(sm.group('score'))
            continue
        tm = TEXT_RE.match(line)
        if tm:
            cur['text'] = tm.group('text')
            continue
        src = SOURCE_RE.match(line)
        if src:
            cur['source'] = src.group('src')
            continue
        if line.startswith('   - [') and len(cur['context']) < MAX_CONTEXT_LINES_PER_ITEM:
            cur['context'].append(line)
    if cur:
        items.append(cur)
    return header, items


def classify(item: dict) -> tuple[int, str, list[str]]:
    blob = ' '.join([item.get('head', ''), item.get('text', ''), item.get('source', '')]).lower()
    markers = item.get('markers', '').lower()
    channel = item.get('channel', '').lower()
    user = item.get('user', '').strip().lower()
    collector_score = int(item.get('score') or 0)
    value = 0
    reasons: list[str] = []

    # --- Hard exclusions first ---
    # Slackbot app install requests — DJ is super admin, gets these automatically. IT handles them.
    if 'would like to install the app' in blob or ('uslackbot' in user and 'install' in blob):
        return -999, 'Hard excluded', ['slackbot app install — IT handles, not DJ']

    is_dm = 'group dm' in markers or 'direct dm' in markers or re.match(r'^(mpdm-|d[A-Z0-9])', channel, re.I)
    is_mention = 'mentions dj' in markers or '<@U05FS0SE77F>' in blob
    is_active_channel = 'recent dj-active channel' in markers
    entities = [e for e in TOM_ENTITIES if e in blob]
    signals = [s for s in EXEC_SIGNALS if s in blob]
    bot_noise = channel in NOISE_CHANNELS or user in BOT_USERS
    in_leasing_channel = bool(LEASING_CHANNELS.search(channel))
    in_priority_channel = channel in PRIORITY_CHANNELS
    in_cleaning_channel = bool(CLEANING_CHANNELS.search(channel))

    # --- Build score ---
    if is_mention:
        value += 130; reasons.append('direct DJ mention')
    if is_dm:
        value += 95; reasons.append('DM/MPIM')
    if is_active_channel:
        value += 75; reasons.append('recent DJ-active channel')
    if entities:
        # Raised entity base from 65 → 90 so single strong entity can surface
        value += 90 + min(35, 8 * len(entities)); reasons.append('ToM entity: ' + ', '.join(entities[:4]))
    if signals:
        value += 45 + min(40, 6 * len(signals)); reasons.append('exec signal: ' + ', '.join(signals[:5]))

    # Priority channels (deal/acquisition/MENA project channels): moderate boost
    if in_priority_channel:
        value += 40; reasons.append('priority deal/project channel')

    # Engineering + entity = product or naming decision worth surfacing
    if channel == 'engineering' and entities:
        value += 30; reasons.append('engineering × ToM entity')

    # Tour/prospect signals in leasing channels = valuable to DJ
    leasing_hits = [s for s in LEASING_SIGNALS if s in blob]
    if in_leasing_channel and leasing_hits:
        value += 120; reasons.append('leasing/tour signal: ' + ', '.join(leasing_hits[:3]))

    # Collector score contribution (capped — prevents weak keyword floods)
    value += min(collector_score, 35)

    # --- Suppress noise ---
    if bot_noise:
        if not (is_dm or is_mention or entities or any(x in blob for x in ['outage', 'incident', 'degraded', 'argocd', 'yardi-connector'])):
            value -= 200; reasons.append('bot/test noise — hard suppressed')
        else:
            value -= 35; reasons.append('bot/test source')

    # Cleaning/housekeeping channels: pure ops signal, not DJ-level unless major incident
    if in_cleaning_channel:
        value -= 150; reasons.append('cleaning/housekeeping ops — below DJ level')

    # Generic ops chatter with no executive signal or entity
    weak_noise = {'renewal', 'test', 'data', 'build', 'tool', 'future', 'head',
                  'results', 'feature', 'roadmap', 'program', 'launch', 'complete', 'close'}
    if any(w in blob for w in weak_noise) and not (is_dm or is_mention or entities or signals or in_priority_channel or leasing_hits):
        value -= 70; reasons.append('weak generic keyword only')

    # Very short messages without DM/mention/entity context
    text = item.get('text', '').strip()
    if len(text) < 25 and not (is_dm or is_mention or entities):
        value -= 60; reasons.append('low substance')

    # Tier labels for synthesis
    if is_dm or is_mention or (entities and signals):
        tier = 'Needs DJ attention'
    elif entities or signals or in_priority_channel or (in_leasing_channel and leasing_hits):
        tier = 'Worth knowing / monitor'
    else:
        tier = 'Low confidence'

    return value, tier, reasons


def render(header, ranked):
    out = []
    out.append('# Filtered Slack Business Brief Evidence')
    out.append(
        'Executive-relevance pre-filter v3: DMs/MPIMs/mentions, exact ToM entities, '
        'priority deal channels, tour/prospect leasing signals, engineering product decisions. '
        'Hard-excluded: Slackbot install requests, pure bot noise, generic ops chatter.'
    )
    out.append('')
    for line in header:
        if line.startswith('Collected at:') or 'DM conversations scanned:' in line or \
           'Candidate items emitted:' in line or 'Window start date:' in line:
            out.append(line)
    out.append(f'Filtered candidate items emitted: {len(ranked)}')
    out.append('')
    out.append('## Candidate Slack items')
    if not ranked:
        out.append('No Slack items crossed the executive relevance threshold.')
    for i, (value, tier, reasons, item) in enumerate(ranked, 1):
        head = ITEM_RE.sub(
            lambda m: f"{i}. [{m.group('time')}] #{m.group('channel')}{m.group('markers')} — {m.group('user')}",
            item['head']
        )
        out.append(head)
        out.append(f'   Relevance: {tier}; score {value}; kept because: {"; ".join(reasons) or "collector signal"}')
        out.append(f'   Text: {truncate(item.get("text", ""))}')
        if item.get('source'):
            out.append(f'   {item["source"]}')
        if item.get('context'):
            out.append('   Context:')
            out.extend(item['context'])
    return '\n'.join(out) + '\n'


def main():
    if not LATEST.exists():
        print('# Filtered Slack Business Brief Evidence\\nNo Slack collection file found.')
        return
    header, items = parse(LATEST.read_text(errors='ignore'))

    high_signal = []
    channel_pulse = []

    for item in items:
        value, tier, reasons = classify(item)
        if value >= 105:
            high_signal.append((value, tier, reasons, item))
        elif value >= 20 and tier != 'Low confidence':
            # Include lower-scoring items as business-pulse context so the model
            # can synthesize what's happening across the workspace — not just DMs.
            channel_pulse.append((value, tier, reasons, item))

    high_signal.sort(key=lambda x: x[0], reverse=True)
    channel_pulse.sort(key=lambda x: x[0], reverse=True)

    # Dedup channel_pulse against high_signal by channel (keep at most 1 rep per channel)
    seen_channels_pulse = {item['channel'] for _, _, _, item in high_signal}
    deduped_pulse = []
    for entry in channel_pulse:
        ch = entry[3].get('channel', '')
        if ch not in seen_channels_pulse:
            seen_channels_pulse.add(ch)
            deduped_pulse.append(entry)
        if len(deduped_pulse) >= MAX_ITEMS_CHANNEL_PULSE:
            break

    ranked = high_signal[:MAX_ITEMS] + deduped_pulse
    print(render(header, ranked))


if __name__ == '__main__':
    main()
