#!/usr/bin/env python3
"""Extract high-signal Slack crawl items into Daily ToM intake candidates.

Input: /opt/data/slack_business_brief_latest.md, produced by slack_business_brief_collect.py
Output: /opt/data/daily-tom/slack_intake.json

This is intentionally conservative and deterministic: it creates review/follow-up
candidates only for high-scoring Slack items, DMs/MPIMs, mentions, and urgent/blocker
language. It never sends/responds in Slack.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

IN = Path('/opt/data/slack_business_brief_latest.md')
OUT = Path('/opt/data/daily-tom/slack_intake.json')
STATE = Path('/opt/data/daily-tom/slack_intake_state.json')
MAX_ITEMS = 8
MIN_SCORE = 70

ITEM_RE = re.compile(r"^\d+\. \[(?P<time>[^\]]+)\] #(?P<channel>[^\s(]+)(?P<markers>.*?) — (?P<user>.+)$")
SCORE_RE = re.compile(r"^\s*Score:\s*(\d+)")
TEXT_RE = re.compile(r"^\s*Text:\s*(.+)$")
SOURCE_RE = re.compile(r"^\s*Source:\s*.*? — (?P<url>\S+)\s*$")
PRIORITY_WORDS = re.compile(r"\b(urgent|blocked|blocker|escalat|incident|outage|churn|legal|budget|cash|board|investor|revenue|finance|MENA)\b", re.I)


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return default
    return default


def short_hash(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:5]


def clean_snippet(s: str, n: int = 140) -> str:
    s = re.sub(r"<@[A-Z0-9]+>", "DJ", s)
    s = re.sub(r"<([^|>]+)\|([^>]+)>", r"\2", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > n:
        s = s[: n - 1].rstrip() + "…"
    return s


def parse_items(md: str):
    items = []
    cur = None
    for line in md.splitlines():
        m = ITEM_RE.match(line)
        if m:
            if cur:
                items.append(cur)
            cur = m.groupdict()
            cur['score'] = 0
            cur['text'] = ''
            cur['url'] = ''
            continue
        if cur is None:
            continue
        sm = SCORE_RE.match(line)
        if sm:
            cur['score'] = int(sm.group(1)); continue
        tm = TEXT_RE.match(line)
        if tm:
            cur['text'] = tm.group(1).strip(); continue
        src = SOURCE_RE.match(line)
        if src:
            cur['url'] = src.group('url')
    if cur:
        items.append(cur)
    return items


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not IN.exists():
        OUT.write_text(json.dumps({'generated_at': dt.datetime.utcnow().isoformat()+'Z', 'items': [], 'reason': 'no slack collection file'}, indent=2))
        return
    md = IN.read_text(errors='ignore')
    state = load_json(STATE, {'seen_urls': []})
    seen = set(state.get('seen_urls', []))
    candidates = []
    for item in parse_items(md):
        text = item.get('text') or ''
        markers = item.get('markers') or ''
        score = int(item.get('score') or 0)
        url = item.get('url') or f"{item.get('channel')}:{item.get('time')}:{text[:80]}"
        if url in seen:
            continue
        high_signal = score >= MIN_SCORE or 'mentions DJ' in markers or 'DM' in markers or PRIORITY_WORDS.search(text)
        if not high_signal:
            continue
        channel = item.get('channel') or 'slack'
        group = 'Professional - MENA' if ('mena' in channel.lower() or 'mena' in text.lower()) else 'Professional - Others'
        snippet = clean_snippet(text)
        task_id = 's' + short_hash(url)
        priority = '**' if score >= 100 or 'mentions DJ' in markers else '*'
        task_text = f"Slack: #{channel} — review/follow up: {snippet} {priority} [n:{task_id}]"
        candidates.append({
            'id': task_id,
            'group': group,
            'task_text': task_text,
            'source_url': url,
            'score': score,
            'channel': channel,
            'user': item.get('user'),
            'time': item.get('time'),
            'raw_text': text,
        })
        if len(candidates) >= MAX_ITEMS:
            break
    payload = {
        'generated_at': dt.datetime.utcnow().isoformat()+'Z',
        'source_file': str(IN),
        'items': candidates,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    OUT.chmod(0o600)
    print(f"slack_intake_candidates={len(candidates)}")


if __name__ == '__main__':
    main()
