#!/usr/bin/env python3
import subprocess, sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
kind = sys.argv[1] if len(sys.argv)>1 else 'weekly'
now = datetime.now(ZoneInfo('America/New_York'))
if kind == 'weekly' and not (now.weekday() == 0 and now.hour == 5 and now.minute == 30):
    sys.exit(0)
if kind == 'monthly' and not (now.day == 1 and now.hour == 9 and now.minute == 0):
    sys.exit(0)
if kind == 'quarterly' and not (now.day == 1 and now.month in (1,4,7,10) and now.hour == 9 and now.minute == 0):
    sys.exit(0)
cp = subprocess.run(['/opt/data/scripts/thoughts_system.py','synthesize',kind], text=True, capture_output=True, timeout=360)
if cp.returncode != 0:
    print(f'Thoughts {kind} synthesis failed:\n' + (cp.stderr or cp.stdout)); sys.exit(cp.returncode)
out = cp.stdout.strip()
if kind == 'weekly':
    print(out)
elif kind == 'monthly':
    files = sorted(Path('/opt/data/thoughts-repo/monthly').glob('**/*.md'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print('Monthly thoughts synthesis completed, but no monthly markdown file was found.'); sys.exit(1)
    print('Monthly thoughts synthesis is ready. Markdown file attached below.\n')
    print('MEDIA:' + str(files[0]))
elif kind == 'quarterly':
    files = sorted(Path('/opt/data/thoughts-repo/quarterly').glob('**/*.md'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print('Quarterly thoughts synthesis completed, but no quarterly markdown file was found.'); sys.exit(1)
    print('Quarterly thoughts synthesis is ready. Markdown file attached below.\n')
    print('MEDIA:' + str(files[0]))
