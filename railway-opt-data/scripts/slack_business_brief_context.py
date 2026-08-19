#!/usr/bin/env python3
"""Print context for the Slack executive brief job.

This intentionally includes curated rolling memory/open topics plus the latest
collector evidence. It does not print raw archive dumps beyond bounded recent files.
"""
from pathlib import Path
import re
import subprocess


_INVISIBLE_RE = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff]')


def sanitize(text: str) -> str:
    return _INVISIBLE_RE.sub('', text or '')

archive = Path('/opt/data/slack_brief_archive')
open_topics = archive / 'open_topics.md'
latest = Path('/opt/data/slack_business_brief_latest.md')
dj_followup_trace = Path('/opt/data/slack_dj_followup_trace.md')

print('# Rolling Slack Brief Context')
print()
print('# Daily ToM Priority Lens')
try:
    print(sanitize(subprocess.check_output(['/opt/data/scripts/daily-tom-context.py'], text=True, timeout=120)))
except Exception as e:
    print(f'Unable to load Daily ToM context: {type(e).__name__}')
print()
print('# Lightweight Email Context')
try:
    print(sanitize(subprocess.check_output(['/opt/data/scripts/email-tom-context.py'], text=True, timeout=180)))
except Exception as e:
    print(f'Unable to load email context: {type(e).__name__}')
print()
if open_topics.exists():
    print('## Open / rolling topics from prior briefs')
    print(sanitize(open_topics.read_text(errors='ignore')[:12000]))
else:
    print('## Open / rolling topics from prior briefs')
    print('No rolling topics file found.')

print('\n# DJ Slack Follow-up Trace')
try:
    print(sanitize(subprocess.check_output(['/opt/data/scripts/slack_dj_followup_trace.py'], text=True, timeout=180)))
except Exception as e:
    print(f'Unable to load DJ Slack follow-up trace: {type(e).__name__}')
    if dj_followup_trace.exists():
        print(sanitize(dj_followup_trace.read_text(errors='ignore')[:12000]))

print('\n# Latest Slack Collection Evidence')
try:
    print(sanitize(subprocess.check_output(['/opt/data/scripts/slack_business_brief_filter.py'], text=True, timeout=180)))
except Exception as e:
    print(f'Unable to filter Slack evidence: {type(e).__name__}')
    if latest.exists():
        print(sanitize(latest.read_text(errors='ignore')[:20000]))
    else:
        print('No Slack collection file found at /opt/data/slack_business_brief_latest.md')
