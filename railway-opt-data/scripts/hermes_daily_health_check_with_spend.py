#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
STATE_DIR = Path("/opt/data/spend-monitor")
LAST_SENT_FILE = STATE_DIR / "last_daily_health_with_spend_et_date.txt"
HEALTH_SCRIPT = "/opt/data/scripts/chief_health_check.sh"
SPEND_SCRIPT = "/opt/data/scripts/hermes_spend_briefing.py"
PYTHON = "/opt/hermes/.venv/bin/python"


def run_cmd(cmd: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd="/opt/hermes",
        env=env,
        text=True,
        capture_output=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def should_emit(now_et: datetime) -> bool:
    if os.getenv("HERMES_DAILY_HEALTH_SPEND_FORCE") == "1":
        return True
    # Cron wakes at UTC candidates for 5 AM ET across DST. Only emit at the
    # actual local hour, and only once per ET date.
    if now_et.hour != 5:
        return False
    et_date = now_et.strftime("%Y-%m-%d")
    try:
        if LAST_SENT_FILE.exists() and LAST_SENT_FILE.read_text().strip() == et_date:
            return False
    except Exception:
        pass
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LAST_SENT_FILE.write_text(et_date)
    return True


def main() -> int:
    now_et = datetime.now(ET)
    if not should_emit(now_et):
        return 0

    health_env = os.environ.copy()
    health_env["CHIEF_HEALTH_ALWAYS_REPORT"] = "1"
    health_rc, health_out, health_err = run_cmd(["bash", HEALTH_SCRIPT], env=health_env)

    spend_env = os.environ.copy()
    spend_env["HERMES_SPEND_REPORT_FORCE"] = "1"
    spend_rc, spend_out, spend_err = run_cmd([PYTHON, SPEND_SCRIPT], env=spend_env)

    print("## Hermes Daily Health Check + Spend Briefing")
    print(f"As of: {now_et.strftime('%a %b %-d, %-I:%M %p ET')}")
    print("")

    print("**Health check**")
    if health_out.strip():
        print(health_out.rstrip())
    else:
        print("(no output)")
    if health_err.strip():
        print("")
        print("Health stderr:")
        print(health_err.rstrip())

    print("")
    print("**Spend briefing**")
    if spend_out.strip():
        print(spend_out.rstrip())
    else:
        print("(no output)")
    if spend_err.strip():
        print("")
        print("Spend stderr:")
        print(spend_err.rstrip())

    if health_rc != 0 or spend_rc != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
