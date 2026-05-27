#!/usr/bin/env python3
"""Lightweight Gmail context for the single ToM-aware business briefing.

Read-only. Searches personal + 166-2nd Gmail with bounded queries only:
- small recent inbox/unread windows
- small query set derived from Daily ToM keywords
It does not scan the whole mailbox and never sends/modifies email.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import OrderedDict

ACCOUNTS = ['personal', '166-2nd']
MAX_RECENT = 8
MAX_PER_QUERY = 4
MAX_OUTPUT_PER_ACCOUNT = 12
TOM_CONTEXT_CMD = ['/opt/data/scripts/daily-tom-context.py']

STOP = {
    'the','and','for','with','from','this','that','review','follow','setup','complete','launch',
    'check','read','build','update','program','document','details','impact','priority','professional',
    'personal','others','current','context','section','daily','mind','task','tasks','head','moc',
    'overview','deals','future','feature','request','operations','structure','template','close',
    'renewal','upsell','training','programs','results','diagnosis','experience','build','late',
    'fees','safe','shares','transfer','subscription','shutdown'
}


def run_json(cmd, timeout=90):
    out = subprocess.check_output(cmd, text=True, timeout=timeout)
    if out.strip().startswith('No messages found') or not out.strip():
        return []
    return json.loads(out)


def clean(s: str, n=220) -> str:
    s = re.sub(r'\s+', ' ', s or '').strip()
    return s[:n-1].rstrip() + '…' if len(s) > n else s


def tom_keywords() -> list[str]:
    try:
        txt = subprocess.check_output(TOM_CONTEXT_CMD, text=True, timeout=120)
    except Exception:
        return ['MENA', 'SICO', 'board', 'Easton', 'Wynwood', 'F&B', 'revenue']
    # Pull capitalized/specific terms and known prefixes from current ToM.
    terms = []
    for line in txt.splitlines():
        if not line.startswith('- '):
            continue
        body = re.sub(r'\[.*?\]', '', line[2:])
        for m in re.finditer(r"[A-Za-z][A-Za-z0-9&'/-]{2,}", body):
            w = m.group(0).strip('-')
            if len(w) < 3 or w.lower() in STOP:
                continue
            if w.lower().startswith('priority'):
                continue
            terms.append(w)
    # Preserve order but cap. Include only terms that are likely useful Gmail search keys.
    preferred = []
    for t in terms:
        if t.upper() == 'MENA' or t in {'SICO','Easton','Wynwood','Board','Olaya','Hubspot','F&B','XM','VP'} or len(t) >= 5:
            preferred.append(t)
    out = list(OrderedDict.fromkeys(preferred))[:18]
    # Add high-signal multiword/business terms from the actual ToM; these are less noisy than generic single words.
    anchors = ['Easton', 'Wynwood', 'Flow overview', 'Board deck', 'MENA', 'SICO', 'Olaya', 'Hubspot', 'F&B', 'renewal upsell', 'leasing data', 'late fees', 'XM comp']
    out = list(OrderedDict.fromkeys(anchors + out))[:18]
    return out or ['MENA', 'SICO', 'board deck', 'Easton', 'Wynwood', 'F&B', 'revenue']


def score_msg(m, query=''):
    text = ' '.join([m.get('from',''), m.get('subject',''), m.get('snippet','')]).lower()
    score = 0
    reasons = []
    labels = m.get('labels') or []
    if 'UNREAD' in labels:
        score += 10; reasons.append('unread')
    if 'IMPORTANT' in labels:
        score += 8; reasons.append('important')
    if query and query.lower() in text:
        score += 45; reasons.append('ToM match: ' + query)
    for term in ['urgent','asap','blocked','contract','signature','legal','wire','payment','invoice','board deck','investor','sico','mena','easton','wynwood','revenue','finance','f&b','olaya','hubspot']:
        if term in text:
            score += 15; reasons.append(term)
    # Suppress newsletters/marketing unless they directly match a strong ToM entity.
    noisy = any(x in text for x in ['newsletter', 'view in browser', 'manage your notification', 'unsubscribe', 'substack.com', 'nytimes.com', 'onetravelspecials.com'])
    strong = any(x in text for x in ['easton','wynwood','sico','mena','olaya','hubspot','f&b'])
    if noisy and not strong:
        score -= 40; reasons.append('newsletter/noise')
    return score, sorted(set(reasons))[:6]


def search(account, query, maxn):
    try:
        return run_json(['/opt/data/scripts/google-account', account, 'gmail', 'search', query, '--max', str(maxn)])
    except Exception as e:
        return {'error': type(e).__name__, 'query': query}


def main():
    kws = tom_keywords()
    print('# Lightweight Email Context')
    print('Read-only bounded Gmail search. Accounts: personal, 166-2nd. No send/modify. Queries are recent and ToM-keyword capped.')
    print('ToM keyword lens: ' + ', '.join(kws[:18]))
    print()

    for account in ACCOUNTS:
        seen = {}
        errors = []
        queries = [
            'in:inbox newer_than:2d -category:promotions -category:social',
            'in:inbox is:unread newer_than:7d -category:promotions -category:social',
        ]
        for kw in kws[:10]:
            # Keep query light: recent inbox only; quote multiword terms.
            qkw = f'"{kw}"' if ' ' in kw else kw
            queries.append(f'in:inbox newer_than:14d {qkw}')

        for q in queries:
            res = search(account, q, MAX_PER_QUERY if q not in queries[:2] else MAX_RECENT)
            if isinstance(res, dict) and res.get('error'):
                errors.append(f'{q}: {res["error"]}')
                continue
            for m in res or []:
                mid = m.get('id')
                if not mid:
                    continue
                score, reasons = score_msg(m, q.split()[-1].strip('"'))
                existing = seen.get(mid)
                item = {
                    'id': mid,
                    'from': clean(m.get('from',''), 120),
                    'subject': clean(m.get('subject',''), 180),
                    'date': m.get('date',''),
                    'snippet': clean(m.get('snippet',''), 260),
                    'labels': m.get('labels') or [],
                    'score': score,
                    'reasons': reasons,
                    'matched_query': q,
                    'account': account,
                }
                if existing is None or score > existing['score']:
                    seen[mid] = item

        items = sorted([x for x in seen.values() if x['score'] >= 35], key=lambda x: (x['score'], x.get('date','')), reverse=True)[:MAX_OUTPUT_PER_ACCOUNT]
        print(f'## {account} Gmail')
        if errors:
            print('Search errors: ' + '; '.join(errors[:3]))
        if not items:
            print('No high-signal recent inbox items found in bounded search.')
            print()
            continue
        for i, m in enumerate(items, 1):
            print(f'{i}. Score {m["score"]} ({", ".join(m["reasons"]) or "recent"})')
            print(f'   From: {m["from"]}')
            print(f'   Subject: {m["subject"]}')
            print(f'   Date: {m["date"]}')
            print(f'   Snippet: {m["snippet"]}')
            print(f'   Query: `{m["matched_query"]}`')
        print()


if __name__ == '__main__':
    main()
