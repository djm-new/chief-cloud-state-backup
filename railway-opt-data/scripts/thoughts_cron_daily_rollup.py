#!/usr/bin/env python3
import subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo
now = datetime.now(ZoneInfo('America/New_York'))
if not (now.hour == 0 and now.minute == 5):
    sys.exit(0)
cp = subprocess.run(['/opt/data/scripts/thoughts_system.py','rollup'], text=True, capture_output=True)
if cp.returncode != 0:
    print('Thoughts daily rollup failed:\n' + (cp.stderr or cp.stdout))
    sys.exit(cp.returncode)
