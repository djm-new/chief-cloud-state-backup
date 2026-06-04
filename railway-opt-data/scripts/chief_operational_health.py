#!/usr/bin/env python3
"""Chief operational health checks for briefing/ToM memory-adjacent systems.

Prints a compact report. Silent success/failure handling is controlled by caller.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone

NOW = time.time()
ISSUES: list[str] = []
LINES: list[str] = []


def age_hours(p: Path) -> float | None:
    if not p.exists():
        return None
    return (NOW - p.stat().st_mtime) / 3600


def check_file(path: str, max_age_h: float | None = None, max_size_kb: int | None = None, min_size: int = 1):
    p = Path(path)
    if not p.exists():
        ISSUES.append(f"Missing file: {path}")
        LINES.append(f"{path}: MISSING")
        return
    st = p.stat()
    age = age_hours(p)
    LINES.append(f"{path}: {st.st_size} bytes, age {age:.1f}h")
    if st.st_size < min_size:
        ISSUES.append(f"File appears empty: {path}")
    if max_age_h is not None and age is not None and age > max_age_h:
        ISSUES.append(f"Stale file: {path} age {age:.1f}h > {max_age_h}h")
    if max_size_kb is not None and st.st_size > max_size_kb * 1024:
        ISSUES.append(f"Hot file too large: {path} {st.st_size/1024:.1f}KB > {max_size_kb}KB")


def run_check(name: str, cmd: list[str], timeout: int = 60, must_contain: list[str] | None = None):
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=timeout)
        LINES.append(f"{name}: OK ({len(out)} chars)")
        for needle in must_contain or []:
            if needle not in out:
                ISSUES.append(f"{name} output missing expected marker: {needle}")
    except Exception as e:
        ISSUES.append(f"{name} failed: {type(e).__name__}: {e}")
        LINES.append(f"{name}: FAIL")


def smart_briefing_jobs_paused() -> bool:
    try:
        data = json.loads(Path('/opt/data/cron/jobs.json').read_text())
    except Exception:
        return False
    wanted = {'Smart business briefing data collection', 'Smart business briefing'}
    states = {}
    for job in data.get('jobs', []):
        name = job.get('name')
        if name in wanted:
            states[name] = (not job.get('enabled')) or job.get('state') == 'paused'
    return wanted.issubset(states) and all(states.values())


briefing_paused = smart_briefing_jobs_paused()

# Freshness / existence checks.
check_file('/opt/data/daily-tom/task_state.json', max_age_h=72, max_size_kb=256)
if briefing_paused:
    LINES.append('Smart briefing freshness: skipped because smart briefing cron jobs are paused')
    check_file('/opt/data/slack_business_brief_latest.md', max_size_kb=512)
else:
    check_file('/opt/data/slack_business_brief_latest.md', max_age_h=72, max_size_kb=512)
check_file('/opt/data/slack_brief_archive/open_topics.md', max_size_kb=12)
check_file('/opt/data/slack_brief_archive/BRIEFING_POLICY.md', max_size_kb=16)
check_file('/opt/data/google-accounts/SECURITY_POLICY.md', max_size_kb=16)
check_file('/opt/data/security/ATTACK_VECTOR_CHECKLIST.md', max_size_kb=24)

# At least one archived briefing eventually. Warning only after system is active.
archive_dir = Path('/opt/data/slack_brief_archive')
briefs = sorted(archive_dir.glob('20*-*.md')) if archive_dir.exists() else []
LINES.append(f"Archived smart briefings: {len(briefs)}")
if briefs:
    age = age_hours(briefs[-1])
    LINES.append(f"Latest archived briefing: {briefs[-1].name}, age {age:.1f}h")
    if not briefing_paused and age is not None and age > 96:
        ISSUES.append(f"Latest archived briefing is stale: {age:.1f}h")

# Context generation must include all major sections.
run_check('Daily ToM context', ['/opt/data/scripts/daily-tom-context.py'], timeout=90, must_contain=['## Daily Top of Mind Context'])
run_check('Email ToM context', ['/opt/data/scripts/email-tom-context.py'], timeout=180, must_contain=['# Lightweight Email Context', '## personal Gmail', '## 166-2nd Gmail'])
run_check('Filtered Slack context', ['/opt/data/scripts/slack_business_brief_filter.py'], timeout=180, must_contain=['# Filtered Slack Business Brief Evidence'])
run_check('Full smart brief context', ['python3', '/opt/data/scripts/slack_business_brief_context.py'], timeout=240, must_contain=['# Daily ToM Priority Lens', '# Lightweight Email Context', '# Latest Slack Collection Evidence'])

print(f"Chief operational health: {datetime.now(timezone.utc).isoformat()}")
for line in LINES:
    print(f"Check: {line}")
if ISSUES:
    print('Status: ATTENTION NEEDED')
    for issue in ISSUES:
        print(f"Issue: {issue}")
    raise SystemExit(1)
print('Status: OK')
