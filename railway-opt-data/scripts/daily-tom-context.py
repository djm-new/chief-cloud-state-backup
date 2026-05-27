#!/usr/bin/env python3
"""Extract the active Daily ToM section for Slack-brief context.

Read-only. Never writes to Google Docs.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict

DOC_ID = '10KsXkvIR0Je4J_dGkv0PI-4Mngb5db3MSstjnEU8Gpw'
DATE_RE = re.compile(r'^(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)\s+\d{1,2},\s+\d{4}(?:\s+-\s+Week Ahead)?$')
SECTION_RE = re.compile(r'^\[(.+?)\]$')
PRIORITY_RE = re.compile(r'(?<!\*)\*{1,3}(?!\*)')
ID_RE = re.compile(r'\[n:([A-Za-z0-9]{4,12})\]')
DONE_RE = re.compile(r'^(?:✅\s*|\[x\]\s*|[xX]\s+)')


def fetch_body() -> str:
    out = subprocess.check_output(['/opt/data/scripts/google-account', 'personal', 'docs', 'get', DOC_ID], text=True, timeout=90)
    return json.loads(out).get('body', '')


def main():
    try:
        body = fetch_body()
    except Exception as e:
        print(f'## Daily ToM Context\nUnable to fetch Daily ToM: {type(e).__name__}')
        return
    lines = [x.rstrip() for x in body.splitlines()]
    date_idx = next((i for i, l in enumerate(lines) if DATE_RE.match(l.strip())), None)
    if date_idx is None:
        print('## Daily ToM Context\nNo dated section found.')
        return
    end_idx = next((i for i in range(date_idx + 1, len(lines)) if DATE_RE.match(lines[i].strip())), len(lines))
    date_label = lines[date_idx].strip()
    by_section = defaultdict(list)
    section = None
    for raw in lines[date_idx + 1:end_idx]:
        t = raw.strip()
        if not t:
            continue
        sm = SECTION_RE.match(t)
        if sm:
            section = sm.group(1)
            continue
        if not section or DONE_RE.match(t):
            continue
        priority = max([len(m.group(0)) for m in PRIORITY_RE.finditer(t)] or [0])
        task_id = (ID_RE.search(t).group(1) if ID_RE.search(t) else '')
        clean = re.sub(r'^(?:↗️\s*|\[>\]\s*|>\s*)', '', t).strip()
        by_section[section].append({'text': clean, 'priority': priority, 'id': task_id})

    print('## Daily Top of Mind Context')
    print(f'Current ToM section: {date_label}')
    print('Use these as the priority lens for the Slack briefing. Highlight Slack activity that maps to these items; do not create or edit ToM items.')
    print()
    for sec in ['Professional', 'Professional - MENA', 'Professional - Others', 'Personal']:
        items = by_section.get(sec, [])
        if not items:
            continue
        print(f'### {sec}')
        # Put starred items first, then original order.
        for item in sorted(items, key=lambda x: -x['priority']):
            p = ' [priority:' + '*' * item['priority'] + ']' if item['priority'] else ''
            tid = f" [{item['id']}]" if item['id'] else ''
            print(f'- {item["text"]}{p}{tid}')
        print()


if __name__ == '__main__':
    main()
