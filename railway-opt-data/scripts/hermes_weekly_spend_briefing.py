#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from hermes_state import SessionDB
from agent.insights import InsightsEngine
from hermes_constants import get_hermes_home

ET = ZoneInfo("America/New_York")
STATE_DIR = get_hermes_home() / "spend-monitor"
LAST_SENT_FILE = STATE_DIR / "last_weekly_briefing_et_week.txt"


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


def top_models(report: dict, max_rows: int = 4) -> list[str]:
    rows = report.get("models", []) or []
    if not rows:
        return ["- No sessions found."]
    lines = []
    for row in rows[:max_rows]:
        model = row.get("model") or "unknown"
        cost = usd(row.get("cost"))
        status = row.get("cost_status") or "unknown"
        lines.append(
            f"- {model}: {cost} · {num(row.get('sessions'))} sessions · {num(row.get('total_tokens'))} tokens · {status}"
        )
    return lines


def top_platforms(report: dict, max_rows: int = 4) -> list[str]:
    rows = report.get("platforms", []) or []
    if not rows:
        return ["- No sessions found."]
    lines = []
    for row in rows[:max_rows]:
        platform = row.get("platform") or "unknown"
        lines.append(
            f"- {platform}: {num(row.get('sessions'))} sessions · {num(row.get('messages'))} messages · {num(row.get('total_tokens'))} tokens"
        )
    return lines


def should_emit(now_et: datetime) -> bool:
    if os.getenv("HERMES_SPEND_REPORT_FORCE") == "1":
        return True
    # Cron wakes at UTC candidates for 5 AM ET across DST. Only emit at the
    # actual local hour, only on Mondays, and only once per ISO week.
    if now_et.hour != 5 or now_et.weekday() != 0:
        return False
    iso_year, iso_week, _ = now_et.isocalendar()
    week_key = f"{iso_year}-W{iso_week:02d}"
    try:
        if LAST_SENT_FILE.exists() and LAST_SENT_FILE.read_text().strip() == week_key:
            return False
    except Exception:
        pass
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LAST_SENT_FILE.write_text(week_key)
    return True


def load_report(days: int) -> dict:
    db = SessionDB()
    try:
        engine = InsightsEngine(db)
        return engine.generate(days=days)
    finally:
        db.close()


def render_window(label: str, report: dict) -> list[str]:
    o = report.get("overview", {}) or {}
    lines = [f"**{label}**"]
    lines.append(f"- Estimated spend: {usd(o.get('estimated_cost'))}")
    lines.append(f"- Actual billed spend: {usd(o.get('actual_cost'))}")
    lines.append(f"- Sessions: {num(o.get('total_sessions'))} · Tokens: {num(o.get('total_tokens'))}")
    lines.append(
        f"- Included sessions: {num(o.get('included_cost_sessions'))} · Unknown pricing sessions: {num(o.get('unknown_cost_sessions'))}"
    )
    return lines


def main() -> int:
    now_et = datetime.now(ET)
    if not should_emit(now_et):
        return 0

    weekly = load_report(7)
    daily = load_report(1)

    print("## Hermes Weekly Spend Briefing")
    print(f"As of: {now_et.strftime('%a %b %-d, %-I:%M %p ET')}")
    print("")
    print("\n".join(render_window("Last 7d", weekly)))
    print("")
    print("\n".join(render_window("Last 24h", daily)))
    print("")
    print("**Top models — last 7d**")
    print("\n".join(top_models(weekly)))
    print("")
    print("**Top platforms — last 7d**")
    print("\n".join(top_platforms(weekly)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
