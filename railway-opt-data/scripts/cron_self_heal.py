#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CRON_ROOT = Path("/opt/data/cron")
OUTPUT_ROOT = CRON_ROOT / "output"
JOBS_JSON = CRON_ROOT / "jobs.json"
STATE_DIR = CRON_ROOT / "self-heal"
SEEN_FILE = STATE_DIR / "seen_failures.json"
LAST_SCAN_FILE = STATE_DIR / "last_scan_epoch.txt"
SCRIPT_DIRS = [
    Path("/opt/data/scripts"),
    Path("/opt/data/github/chief-cloud-state-backup/railway-opt-data/scripts"),
]
SPEND_HELPER_NAME = "spend_report_helper.py"
SPEND_SCRIPTS = {"hermes_spend_briefing.py", "hermes_weekly_spend_briefing.py"}

TARGET_IMPORT_BLOCK = "from spend_report_helper import summarize_spend\n"
TARGET_STATE_BLOCK = (
    'ET = ZoneInfo("America/New_York")\n'
    'STATE_DIR = Path(os.getenv("HERMES_HOME", "").strip() or (Path.home() / ".hermes")) / "spend-monitor"\n'
)
TARGET_STATE_BLOCK_WITH_FILE = (
    'ET = ZoneInfo("America/New_York")\n'
    'STATE_DIR = Path(os.getenv("HERMES_HOME", "").strip() or (Path.home() / ".hermes")) / "spend-monitor"\n'
    'LAST_SENT_FILE = STATE_DIR / "last_daily_briefing_et_date.txt"\n'
)
TARGET_STATE_BLOCK_WITH_WEEK = (
    'ET = ZoneInfo("America/New_York")\n'
    'STATE_DIR = Path(os.getenv("HERMES_HOME", "").strip() or (Path.home() / ".hermes")) / "spend-monitor"\n'
    'LAST_SENT_FILE = STATE_DIR / "last_weekly_briefing_et_week.txt"\n'
)

TARGET_IMPORT_REPLACEMENTS = {
    'from agent.spend_ledger import summarize_spend\nfrom hermes_constants import get_hermes_home\n': TARGET_IMPORT_BLOCK,
    'from hermes_constants import get_hermes_home\nfrom spend_report_helper import summarize_spend\n': TARGET_IMPORT_BLOCK,
    'from agent.spend_ledger import summarize_spend\n': TARGET_IMPORT_BLOCK,
    'from hermes_constants import get_hermes_home\n': '',
}


@dataclass
class Failure:
    path: Path
    job_id: str
    job_name: str
    script: str
    text: str


def load_seen() -> set[str]:
    try:
        data = json.loads(SEEN_FILE.read_text())
        if isinstance(data, list):
            return {str(x) for x in data}
    except Exception:
        pass
    return set()



def save_seen(seen: set[str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2))



def load_last_scan_epoch() -> float | None:
    try:
        return float(LAST_SCAN_FILE.read_text().strip())
    except Exception:
        return None



def save_last_scan_epoch(epoch: float) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LAST_SCAN_FILE.write_text(f"{epoch:.6f}")



def load_jobs() -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(JOBS_JSON.read_text())
        jobs = data.get("jobs") if isinstance(data, dict) else data
        out: dict[str, dict[str, Any]] = {}
        if isinstance(jobs, list):
            for job in jobs:
                if isinstance(job, dict):
                    jid = job.get("id") or job.get("job_id")
                    if jid:
                        out[str(jid)] = job
        return out
    except Exception:
        return {}



def find_recent_failures(since_epoch: float | None = None, hours: int = 48) -> list[Failure]:
    if not OUTPUT_ROOT.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    failures: list[Failure] = []
    jobs = load_jobs()
    for path in sorted(OUTPUT_ROOT.glob("*/*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            mtime = path.stat().st_mtime
            if datetime.fromtimestamp(mtime, timezone.utc) < cutoff:
                continue
            if since_epoch is not None and mtime <= since_epoch:
                continue
            text = path.read_text(errors="replace")
        except Exception:
            continue
        if "Status: script failed" not in text and "Status: failed" not in text:
            continue
        job_id = path.parent.name
        job = jobs.get(job_id, {})
        failures.append(
            Failure(
                path=path,
                job_id=job_id,
                job_name=str(job.get("name") or job_id),
                script=str(job.get("script") or ""),
                text=text,
            )
        )
    return failures



def ensure_helper(script_dir: Path) -> bool:
    src = SCRIPT_DIRS[0] / SPEND_HELPER_NAME
    dst = script_dir / SPEND_HELPER_NAME
    if not src.exists():
        return False
    try:
        if not dst.exists() or dst.read_text() != src.read_text():
            dst.write_text(src.read_text())
            return True
    except Exception:
        return False
    return False



def repair_spend_briefing(script_path: Path) -> list[str]:
    changes: list[str] = []
    if not script_path.exists():
        return changes
    text = script_path.read_text()
    original = text

    # Normalize imports.
    text = text.replace(
        'from agent.spend_ledger import summarize_spend\nfrom hermes_constants import get_hermes_home\n',
        'from spend_report_helper import summarize_spend\n',
    )
    text = text.replace(
        'from hermes_constants import get_hermes_home\nfrom spend_report_helper import summarize_spend\n',
        'from spend_report_helper import summarize_spend\n',
    )
    text = text.replace('from agent.spend_ledger import summarize_spend\n', 'from spend_report_helper import summarize_spend\n')
    text = text.replace('from hermes_constants import get_hermes_home\n', '')

    # Normalize the Hermes home resolution.
    text = text.replace(
        'ET = ZoneInfo("America/New_York")\nSTATE_DIR = get_hermes_home() / "spend-monitor"\n',
        'ET = ZoneInfo("America/New_York")\nSTATE_DIR = Path(os.getenv("HERMES_HOME", "").strip() or (Path.home() / ".hermes")) / "spend-monitor"\n',
    )
    # Keep the expected sent-file line in place if it got lost in a bad edit.
    if script_path.name == "hermes_spend_briefing.py" and 'LAST_SENT_FILE = STATE_DIR / "last_daily_briefing_et_date.txt"' not in text:
        text = text.replace(
            'STATE_DIR = Path(os.getenv("HERMES_HOME", "").strip() or (Path.home() / ".hermes")) / "spend-monitor"\n',
            'STATE_DIR = Path(os.getenv("HERMES_HOME", "").strip() or (Path.home() / ".hermes")) / "spend-monitor"\nLAST_SENT_FILE = STATE_DIR / "last_daily_briefing_et_date.txt"\n',
            1,
        )
    if script_path.name == "hermes_weekly_spend_briefing.py" and 'LAST_SENT_FILE = STATE_DIR / "last_weekly_briefing_et_week.txt"' not in text:
        text = text.replace(
            'STATE_DIR = Path(os.getenv("HERMES_HOME", "").strip() or (Path.home() / ".hermes")) / "spend-monitor"\n',
            'STATE_DIR = Path(os.getenv("HERMES_HOME", "").strip() or (Path.home() / ".hermes")) / "spend-monitor"\nLAST_SENT_FILE = STATE_DIR / "last_weekly_briefing_et_week.txt"\n',
            1,
        )

    if text != original:
        script_path.write_text(text)
        changes.append(f"repaired {script_path}")
    return changes



def parse_failure(failure: Failure) -> tuple[str, bool]:
    text = failure.text
    job = failure.job_name
    script = failure.script or Path(failure.path).name
    if not script:
        return (f"⚠️ Cron failure needs attention: {job}\n- Could not determine script name from job metadata.", False)

    if (
        script in SPEND_SCRIPTS
        and ("ModuleNotFoundError: No module named 'agent'" in text or "ModuleNotFoundError: No module named 'hermes_constants'" in text)
    ):
        changed: list[str] = []
        for script_dir in SCRIPT_DIRS:
            helper_fixed = ensure_helper(script_dir)
            if helper_fixed:
                changed.append(f"copied {SPEND_HELPER_NAME} into {script_dir}")
            script_path = script_dir / script
            changed.extend(repair_spend_briefing(script_path))
        if changed:
            return (
                f"ℹ️ Auto-repaired Hermes spend briefing\n- Job: {job}\n- Fixes: {', '.join(changed)}\n- DJ action: none.",
                True,
            )
        return (
            f"⚠️ Hermes spend briefing needs attention\n- Job: {job}\n- The script failed with import-path issues, but I could not patch it automatically.\n- DJ action: review the spend briefing scripts.",
            False,
        )

    if "git push to GitHub failed" in text:
        return (
            f"⚠️ Backup sync failed\n- Job: {job}\n- Reason: git push to GitHub failed.\n- Likely cause: auth or repo-link issue.\n- DJ action: check GITHUB_TOKEN and repo access.",
            False,
        )

    if "Script not found" in text:
        return (
            f"⚠️ Cron script missing\n- Job: {job}\n- Reason: the configured script path could not be found.\n- DJ action: fix the cron job script path or restore the file.",
            False,
        )

    if "ModuleNotFoundError" in text:
        return (
            f"⚠️ Cron job import failure\n- Job: {job}\n- Script: {script}\n- I saw a ModuleNotFoundError, but there is no known auto-repair for this case yet.\n- DJ action: inspect the traceback in {failure.path}",
            False,
        )

    return (
        f"⚠️ Cron job failed\n- Job: {job}\n- Script: {script}\n- I do not recognize this failure yet.\n- DJ action: inspect {failure.path}",
        False,
    )



def main() -> int:
    seen = load_seen()
    now_epoch = datetime.now(timezone.utc).timestamp()
    last_scan = load_last_scan_epoch()
    if last_scan is None:
        save_last_scan_epoch(now_epoch)
        save_seen(seen)
        return 0

    failures = find_recent_failures(since_epoch=last_scan)
    emitted: list[str] = []
    any_change = False

    for failure in failures:
        key = str(failure.path)
        if key in seen:
            continue
        seen.add(key)
        msg, changed = parse_failure(failure)
        if msg:
            emitted.append(msg)
        any_change = any_change or changed

    save_seen(seen)
    save_last_scan_epoch(now_epoch)

    if not emitted:
        return 0

    # Print one combined message. If we auto-repaired something, keep it brief.
    print("\n\n".join(emitted))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
