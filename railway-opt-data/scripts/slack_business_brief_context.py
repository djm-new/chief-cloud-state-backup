#!/usr/bin/env python3
"""Print context for the Slack executive brief job.

This intentionally includes curated rolling memory/open topics plus the latest
collector evidence. It does not print raw archive dumps beyond bounded recent files.
"""
from pathlib import Path
import subprocess

archive = Path('/opt/data/slack_brief_archive')
open_topics = archive / 'open_topics.md'
latest = Path('/opt/data/slack_business_brief_latest.md')

print('# Rolling Slack Brief Context')
print()
print('# Daily ToM Priority Lens')
try:
    print(subprocess.check_output(['/opt/data/scripts/daily-tom-context.py'], text=True, timeout=120))
except Exception as e:
    print(f'Unable to load Daily ToM context: {type(e).__name__}')
print()
print('# Lightweight Email Context')
try:
    print(subprocess.check_output(['/opt/data/scripts/email-tom-context.py'], text=True, timeout=180))
except Exception as e:
    print(f'Unable to load email context: {type(e).__name__}')
print()
if open_topics.exists():
    print('## Open / rolling topics from prior briefs')
    print(open_topics.read_text(errors='ignore')[:12000])
else:
    print('## Open / rolling topics from prior briefs')
    print('No rolling topics file found.')

# Include the last 2 archived final briefs, if any, as lightweight continuity.
# Exclude review drafts so DJ feedback artifacts do not pollute future synthesis.
briefs = [p for p in sorted(archive.glob('20*-*.md'), key=lambda p: p.name) if '-review' not in p.name]
briefs = briefs[-2:]
if briefs:
    print('\n## Recent final brief archive')
    for p in briefs:
        print(f'\n### {p.name}')
        print(p.read_text(errors='ignore')[:2500])

print('\n# Latest Slack Collection Evidence')
try:
    print(subprocess.check_output(['/opt/data/scripts/slack_business_brief_filter.py'], text=True, timeout=180))
except Exception as e:
    print(f'Unable to filter Slack evidence: {type(e).__name__}')
    if latest.exists():
        print(latest.read_text(errors='ignore')[:20000])
    else:
        print('No Slack collection file found at /opt/data/slack_business_brief_latest.md')
