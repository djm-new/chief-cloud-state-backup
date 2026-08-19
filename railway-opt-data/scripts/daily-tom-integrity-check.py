#!/opt/data/google-accounts/.venv/bin/python
"""Read-only integrity check for DJ's DM Running Daily ToM.

Checks the live Google Doc current section and tomorrow dry-run for the failure
modes that caused the August 2026 mess: duplicate IDs, corrupt IDs, excessive
current-section size, and malformed generated rollover output.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from googleapiclient.discovery import build

SYNC_PATH = "/opt/data/scripts/daily-tom-sync.py"
MAX_CURRENT_TASKS = 60
MAX_NEXT_TASKS = 70
ID_RE_ANY = re.compile(r"\[n:([^\]]+)\]")
ID_RE_GOOD = re.compile(r"^[A-Za-z0-9]{4,12}$")


def load_sync_module():
    spec = importlib.util.spec_from_file_location("daily_tom_sync", SYNC_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def fail(issue: str, details: list[str] | None = None) -> int:
    print("Daily ToM integrity: FAIL")
    print(f"Issue: {issue}")
    for detail in details or []:
        print(f"Detail: {detail}")
    return 1


def main() -> int:
    mod = load_sync_module()
    creds = mod.get_creds("/opt/data/google-accounts/personal")
    docs = build("docs", "v1", credentials=creds, cache_discovery=False)
    doc = docs.documents().get(documentId=mod.DOC_ID).execute()
    paras = mod.extract_paragraphs(doc)
    _, latest_idx, next_date_idx, _, _, _ = mod.find_sections(paras)
    latest_label = paras[latest_idx].text.strip()

    ids: list[str] = []
    corrupt_ids: list[str] = []
    task_lines: list[str] = []
    current_section = None
    for p in paras[latest_idx + 1 : next_date_idx]:
        raw = p.text.strip()
        if not raw:
            continue
        sm = mod.SECTION_RE.match(raw)
        if sm:
            current_section = sm.group(1)
            continue
        if current_section not in mod.GROUP_ORDER:
            continue
        if mod.is_date_line(raw) or raw in ("[Next date]", "[Deferred]", "[Parking Lot]"):
            continue
        task_lines.append(raw)
        for item_id in ID_RE_ANY.findall(raw):
            ids.append(item_id)
            if not ID_RE_GOOD.match(item_id):
                corrupt_ids.append(item_id)

    duplicate_ids = {k: v for k, v in Counter(ids).items() if v > 1}
    issues: list[str] = []
    details: list[str] = []
    if duplicate_ids:
        issues.append("duplicate IDs in current Daily ToM section")
        details.append(f"duplicate_ids={duplicate_ids}")
    if corrupt_ids:
        issues.append("corrupt IDs in current Daily ToM section")
        details.append(f"corrupt_ids={sorted(set(corrupt_ids))}")
    if len(task_lines) > MAX_CURRENT_TASKS:
        issues.append("current Daily ToM section is unexpectedly large")
        details.append(f"current_task_count={len(task_lines)} max={MAX_CURRENT_TASKS}")

    tomorrow = (dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1)).isoformat()
    dry = subprocess.check_output(
        ["/opt/data/google-accounts/.venv/bin/python", SYNC_PATH, "--date", tomorrow],
        text=True,
        timeout=120,
    )
    dry_data = json.loads(dry)
    new_section = dry_data.get("new_section", "")
    next_ids = ID_RE_ANY.findall(new_section)
    next_duplicate_ids = {k: v for k, v in Counter(next_ids).items() if v > 1}
    next_corrupt_ids = [item_id for item_id in next_ids if not ID_RE_GOOD.match(item_id)]
    next_task_count = sum(1 for line in new_section.splitlines() if line.strip() and not mod.is_date_line(line.strip()) and not mod.SECTION_RE.match(line.strip()))
    if next_duplicate_ids:
        issues.append("tomorrow dry-run would generate duplicate IDs")
        details.append(f"next_duplicate_ids={next_duplicate_ids}")
    if next_corrupt_ids:
        issues.append("tomorrow dry-run would generate corrupt IDs")
        details.append(f"next_corrupt_ids={sorted(set(next_corrupt_ids))}")
    if next_task_count > MAX_NEXT_TASKS:
        issues.append("tomorrow dry-run is unexpectedly large")
        details.append(f"next_task_count={next_task_count} max={MAX_NEXT_TASKS}")

    if issues:
        return fail("; ".join(issues), details)

    print("Daily ToM integrity: OK")
    print(f"Latest section: {latest_label}")
    print(f"Current task count: {len(task_lines)}")
    print(f"Tomorrow dry-run task count: {next_task_count}")
    print("Duplicate IDs: none")
    print("Corrupt IDs: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
