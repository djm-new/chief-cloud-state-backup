#!/usr/bin/env python3
"""Lint the latest smart business briefing for repeated issues across sections.

This is intentionally heuristic: it catches the failure mode DJ flagged, where a
single issue is repeated in Executive summary, Needs DJ, and Carry-forward.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE = Path('/opt/data/slack_brief_archive')
START_FILE = ARCHIVE / '.briefing_repetition_lint_start'
SECTION_RE = re.compile(r'^##\s+(.+?)\s*$')
BULLET_RE = re.compile(r'^[-*]\s+')
STOP = {
    'the','and','for','with','from','that','this','should','needs','need','still','today','current',
    'dj','flow','mena','professional','watching','context','summary','approve','decide','assign',
    'tell','give','keep','track','monitor','item','issue','action','explicit','visible','provided',
}
# Domain phrases that should behave like one issue key when repeated.
PHRASES = [
    'mena comp', 'payroll', 'saudi raises', 'raises timing', 'sami', 'weesam',
    'ddec hiring', 'people process', 'olaya budget', 'revised budget',
    'pm licenses', 'gtm tracker', 'lease pacing', 'analytics hub',
    'flow overview', 'proof-point', 'financial reporting', 'support/product',
]


def latest_file() -> Path | None:
    files = sorted(ARCHIVE.glob('20*-*.md'))
    return files[-1] if files else None


def cutoff_ts() -> float | None:
    if not START_FILE.exists():
        return None
    raw = START_FILE.read_text(errors='ignore').strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00')).timestamp()
    except Exception:
        return None


def sectionize(text: str) -> dict[str, list[str]]:
    current = 'preamble'
    sections: dict[str, list[str]] = defaultdict(list)
    for line in text.splitlines():
        m = SECTION_RE.match(line.strip())
        if m:
            current = m.group(1).strip()
            continue
        if BULLET_RE.match(line.strip()):
            sections[current].append(line.strip())
    return sections


def keys_for_bullet(bullet: str) -> set[str]:
    lower = bullet.lower()
    keys = {p for p in PHRASES if p in lower}
    # Add a compact keyword-pair key from meaningful tokens as a fallback.
    words = re.findall(r'[a-z][a-z0-9-]{3,}', lower)
    words = [w for w in words if w not in STOP]
    for i, w in enumerate(words[:8]):
        for v in words[i+1:i+4]:
            if w != v:
                keys.add(f'{w} {v}')
    return keys


def main(path_arg: str | None = None) -> int:
    path = Path(path_arg) if path_arg else latest_file()
    if not path or not path.exists():
        print('Briefing repetition lint: FAIL')
        print('Issue: no briefing file found')
        return 1
    cutoff = cutoff_ts() if path_arg is None else None
    if cutoff is not None and path.stat().st_mtime < cutoff:
        print('Briefing repetition lint: OK')
        print(f'File: {path.name}')
        print('Skipped: latest briefing predates repetition-lint start marker')
        return 0
    text = path.read_text(errors='ignore')
    sections = sectionize(text)
    occurrences: dict[str, set[str]] = defaultdict(set)
    examples: dict[str, list[str]] = defaultdict(list)
    for section, bullets in sections.items():
        for bullet in bullets:
            for key in keys_for_bullet(bullet):
                occurrences[key].add(section)
                if len(examples[key]) < 3:
                    examples[key].append(f'{section}: {bullet}')
    bad = {k: sorted(v) for k, v in occurrences.items() if len(v) >= 3}
    if bad:
        print('Briefing repetition lint: FAIL')
        print(f'File: {path}')
        for key, secs in sorted(bad.items())[:10]:
            print(f'Issue key repeated across {len(secs)} sections: {key} -> {secs}')
            for ex in examples[key]:
                print(f'  Example: {ex[:240]}')
        return 1
    print('Briefing repetition lint: OK')
    print(f'File: {path.name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
