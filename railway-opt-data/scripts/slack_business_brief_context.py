#!/usr/bin/env python3
from pathlib import Path
p = Path('/opt/data/slack_business_brief_latest.md')
if p.exists():
    print(p.read_text(errors='ignore'))
else:
    print('No Slack collection file found at /opt/data/slack_business_brief_latest.md')
