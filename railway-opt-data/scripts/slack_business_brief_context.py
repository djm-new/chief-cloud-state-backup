#!/usr/bin/env python3
"""Print context for the Slack executive brief job.

This intentionally includes curated rolling memory/open topics plus the latest
collector evidence. It does not print raw archive dumps beyond bounded recent files.
"""
from pathlib import Path

archive = Path('/opt/data/slack_brief_archive')
open_topics = archive / 'open_topics.md'
latest = Path('/opt/data/slack_business_brief_latest.md')

print('# Rolling Slack Brief Context')
print()
if open_topics.exists():
    print('## Open / rolling topics from prior briefs')
    print(open_topics.read_text(errors='ignore')[:12000])
else:
    print('## Open / rolling topics from prior briefs')
    print('No rolling topics file found.')

# Include the last 3 archived final briefs, if any, as lightweight continuity.
briefs = sorted(archive.glob('20*-*.md'), key=lambda p: p.name)[-3:]
if briefs:
    print('\n## Recent final brief archive')
    for p in briefs:
        print(f'\n### {p.name}')
        print(p.read_text(errors='ignore')[:6000])

print('\n# Latest Slack Collection Evidence')
if latest.exists():
    print(latest.read_text(errors='ignore'))
else:
    print('No Slack collection file found at /opt/data/slack_business_brief_latest.md')
