#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "/opt/hermes")

from agent.spend_ledger import summarize_spend  # noqa: E402
from hermes_constants import get_hermes_home  # noqa: E402

ET = ZoneInfo("America/New_York")
STATE_DIR = get_hermes_home() / "spend-monitor"
LAST_SENT_FILE = STATE_DIR / "last_daily_briefing_et_date.txt"


def usd(value) -> str:
    try:
        amount = float(value or 0)
    except Exception:
        amount = 0.0
    if amount >= 1:
        return f"${amount:,.2f}"
    return f"${amount:,.4f}"


def num(value) -> str:
    try:
        return f"{int(value or 0):,}"
    except Exception:
        return "0"


def top_lines(report: dict, max_rows: int = 4) -> list[str]:
    rows = report.get("groups", []) or []
    if not rows:
        return ["- No tracked model calls yet."]
    lines = []
    for row in rows[:max_rows]:
        label = row.get("label") or "unknown"
        lines.append(
            f"- {label}: {usd(row.get('estimated_cost_usd'))} · "
            f"{num(row.get('calls'))} calls · {num(row.get('total_tokens'))} tokens"
        )
    return lines


def total_line(label: str, report: dict) -> str:
    total = report.get("total", {}) or {}
    return (
        f"{label}: {usd(total.get('estimated_cost_usd'))} · "
        f"{num(total.get('calls'))} calls · {num(total.get('total_tokens'))} tokens"
    )


def should_emit(now_et: datetime) -> bool:
    if os.getenv("HERMES_SPEND_REPORT_FORCE") == "1":
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

    daily_provider = summarize_spend(days=1, group_by="provider", limit=6)
    weekly_provider = summarize_spend(days=7, group_by="provider", limit=6)
    daily_project = summarize_spend(days=1, group_by="project", limit=5)
    weekly_project = summarize_spend(days=7, group_by="project", limit=5)
    daily_channel = summarize_spend(days=1, group_by="channel", limit=5)

    print("## Hermes Spend Briefing")
    print(f"As of: {now_et.strftime('%a %b %-d, %-I:%M %p ET')}")
    print("")
    print("**Totals**")
    print(f"- {total_line('Last 24h', daily_provider)}")
    print(f"- {total_line('Last 7d', weekly_provider)}")
    print("")
    print("**Top projects — last 24h**")
    print("\n".join(top_lines(daily_project)))
    print("")
    print("**Top channels — last 24h**")
    print("\n".join(top_lines(daily_channel)))
    print("")
    print("**Top providers — last 7d**")
    print("\n".join(top_lines(weekly_provider)))
    print("")
    print("**Top projects — last 7d**")
    print("\n".join(top_lines(weekly_project)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
