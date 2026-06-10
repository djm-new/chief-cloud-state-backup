#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from agent.spend_ledger import summarize_spend
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
        return ["- No model usage yet."]
    lines = []
    for row in rows[:max_rows]:
        model = row.get("model") or "unknown"
        report_cost_value = float(row.get("cost") or 0)
        raw_cost_value = float(row.get("raw_cost", row.get("cost")) or 0)
        report_cost = usd(report_cost_value)
        raw_cost = usd(raw_cost_value)
        status_flags = row.get("status_flags") or []
        status = ",".join(status_flags) if status_flags else (row.get("cost_status") or "unknown")
        calibration_factor = float(row.get("calibration_factor") or 1.0)
        parts = [report_cost, f"{num(row.get('total_tokens'))} tokens", status]
        if abs(raw_cost_value - report_cost_value) > 1e-9:
            parts.insert(1, f"raw {raw_cost}")
        if calibration_factor != 1.0:
            parts.insert(2, f"calib x{calibration_factor:.4f}")
        lines.append(f"- {model}: " + " · ".join(parts))
    return lines


def top_workstreams(report: dict, max_rows: int = 4, model_rows: int = 2) -> list[str]:
    rows = report.get("workstreams", []) or []
    if not rows:
        return ["- No workstreams found."]
    lines = []
    for row in rows[:max_rows]:
        label = row.get("workstream") or "unclassified"
        cost = usd(row.get("cost"))
        tokens = num(row.get("total_tokens"))
        parts = [cost, f"{tokens} tokens"]
        models = row.get("top_models", []) or []
        if models:
            model_bits = []
            for m in models[:model_rows]:
                model_bits.append(f"{m.get('model') or 'unknown'} {usd(m.get('cost'))}")
            parts.append("models: " + ", ".join(model_bits))
        lines.append(f"- {label}: " + " · ".join(parts))
    return lines


def top_channels(report: dict, max_rows: int = 4) -> list[str]:
    rows = report.get("channels", []) or []
    if not rows:
        return ["- No channel/topic labels captured yet."]
    lines = []
    for row in rows[:max_rows]:
        label = row.get("channel") or "unlabeled"
        cost = usd(row.get("cost"))
        tokens = num(row.get("total_tokens"))
        lines.append(f"- {label}: {cost} · {tokens} tokens")
    return lines


def top_telegram_topics(report: dict, max_rows: int = 8) -> list[str]:
    rows = report.get("channels", []) or []
    known_topics = {
        "General/home",
        "Archive/Old Chief",
        "Briefings",
        "Alerts",
        "Daily Brain Dump",
        "Coding",
        "General (ad-hoc/conversational)",
    }
    rows = [
        row for row in rows
        if (row.get("channel") or "") in known_topics
        or (row.get("channel") or "").startswith("Chief Group - Hermes /")
        or (row.get("channel") or "").startswith("topic ")
    ]
    if not rows:
        return ["- No Telegram topic labels captured yet."]
    lines = []
    for row in rows[:max_rows]:
        label = row.get("channel") or "unlabeled"
        cost = usd(row.get("cost"))
        tokens = num(row.get("total_tokens"))
        lines.append(f"- {label}: {cost} · {tokens} tokens")
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
    return summarize_spend(days=days)


def render_window(label: str, report: dict) -> list[str]:
    o = report.get("overview", {}) or {}
    lines = [f"**{label}**"]
    lines.append(f"- Estimated spend: {usd(o.get('estimated_cost'))}")
    lines.append(f"- Tokens: {num(o.get('total_tokens'))}")
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
    print("**By workstream — last 7d**")
    print("\n".join(top_workstreams(weekly, max_rows=6)))
    print("")
    print("**By Telegram topic — last 7d**")
    print("\n".join(top_telegram_topics(weekly)))
    print("")
    print("**By topic/channel — last 7d**")
    print("\n".join(top_channels(weekly)))
    print("")
    print("**Top models — last 7d**")
    print("\n".join(top_models(weekly)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
