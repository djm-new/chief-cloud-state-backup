#!/usr/bin/env python3
import subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo
now = datetime.now(ZoneInfo('America/New_York'))
if not (now.hour == 7 and now.minute == 0):
    sys.exit(0)
cp = subprocess.run(['/opt/data/scripts/thoughts_system.py','replay'], text=True, capture_output=True)
if cp.returncode != 0:
    print('Thoughts morning replay failed:\n' + (cp.stderr or cp.stdout)); sys.exit(cp.returncode)
print(cp.stdout.strip())
