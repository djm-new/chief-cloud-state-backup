#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from spend_report_helper import build_report

ET = ZoneInfo("America/New_York")
STATE_DIR = Path(os.getenv("HERMES_HOME", "").strip() or (Path.home() / ".hermes")) / "spend-monitor"
LAST_SENT_FILE = STATE_DIR / "last_weekly_briefing_et_week.txt"


def usd(value) -> str:
    try:
        amount = float(value or 0)
    except Exception:
        amount = 0.0
    if amount >= 1:
        return f"${amount:,.2f}"
    return f"${amount:,.4f}"


def tokens_compact(value) -> str:
    try:
        n = int(value or 0)
    except Exception:
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:,.1f}M"
    if n >= 1_000:
        return f"{n/1_000:,.1f}K"
    return f"{n:,}"


def num(value) -> str:
    try:
        return f"{int(value or 0):,}"
    except Exception:
        return "0"


def render_window(label: str, report: dict) -> list[str]:
    o = report.get("overview", {}) or {}
    lines = [f"**{label}**"]
    lines.append(f"- Tokens: {num(o.get('total_tokens'))} "
                 f"({tokens_compact(o.get('input_tokens'))} in · {tokens_compact(o.get('output_tokens'))} out · "
                 f"{tokens_compact(o.get('cache_read_tokens'))} cache)")
    lines.append(f"- Estimated spend (API-rate value): {usd(o.get('est_cost'))}")
    if o.get("has_billed"):
        lines.append(f"- Billed spend: {usd(o.get('billed_cost'))}")
    else:
        lines.append("- Billed spend: unavailable (Codex usage is subscription-included)")
    parts = [f"{num(o.get('sessions'))} agent session{'s' if o.get('sessions') != 1 else ''}"]
    if o.get("events"):
        parts.append(f"{num(o.get('events'))} script API calls")
    if o.get("subscription_sessions"):
        parts.append(f"{num(o.get('subscription_sessions'))} subscription-included")
    lines.append(f"- Activity: {', '.join(parts)}")
    if o.get("unpriced_tokens"):
        lines.append(f"- Unpriced tokens (no reference rate): {num(o.get('unpriced_tokens'))}")
    return lines


def render_projects(report: dict, max_rows: int = 8) -> list[str]:
    rows = report.get("projects", []) or []
    if not rows:
        return ["- No usage found."]
    lines = []
    for row in rows[:max_rows]:
        bits = [f"{tokens_compact(row.get('tokens'))} tokens", f"~{usd(row.get('est_cost'))}"]
        count_bits = []
        if row.get("sessions"):
            count_bits.append(f"{row['sessions']} session{'s' if row['sessions'] != 1 else ''}")
        if row.get("events"):
            count_bits.append(f"{row['events']} call{'s' if row['events'] != 1 else ''}")
        if count_bits:
            bits.append(", ".join(count_bits))
        lines.append(f"- {row.get('project')}: " + " · ".join(bits))
    return lines


def render_topics(report: dict, max_rows: int = 8) -> list[str]:
    rows = report.get("telegram_topics", []) or []
    if not rows:
        return ["- No Telegram usage in window."]
    return [
        f"- {row.get('topic')}: {tokens_compact(row.get('tokens'))} tokens · ~{usd(row.get('est_cost'))}"
        for row in rows[:max_rows]
    ]


def render_models(report: dict, max_rows: int = 6) -> list[str]:
    rows = report.get("models", []) or []
    if not rows:
        return ["- No model usage."]
    lines = []
    for row in rows[:max_rows]:
        modes = row.get("billing_modes") or []
        mode_note = "subscription-included" if modes == ["subscription_included"] else (row.get("provider") or "")
        suffix = f" · {mode_note}" if mode_note else ""
        lines.append(
            f"- {row.get('model')}: {tokens_compact(row.get('tokens'))} tokens · ~{usd(row.get('est_cost'))}{suffix}"
        )
    return lines


def render_stages(report: dict, max_rows: int = 5) -> list[str]:
    rows = report.get("stages", []) or []
    if not rows:
        return []
    return [
        f"- {row.get('stage')}: {tokens_compact(row.get('tokens'))} tokens · ~{usd(row.get('est_cost'))}"
        for row in rows[:max_rows]
    ]


def render_top_sessions(report: dict, max_rows: int = 5) -> list[str]:
    rows = [r for r in (report.get("top_sessions") or []) if r.get("est_cost")]
    if not rows:
        return []
    return [
        f"- {row.get('title') or row.get('id')} ({row.get('model')}, {row.get('source')}): "
        f"{tokens_compact(row.get('tokens'))} tokens · ~{usd(row.get('est_cost'))}"
        for row in rows[:max_rows]
    ]


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


def main() -> int:
    now_et = datetime.now(ET)
    if not should_emit(now_et):
        return 0

    weekly = build_report(7)
    daily = build_report(1)

    print("## Hermes Weekly Spend Briefing")
    print(f"As of: {now_et.strftime('%a %b %-d, %-I:%M %p ET')}")
    print("")
    print("\n".join(render_window("Last 7d", weekly)))
    print("")
    print("\n".join(render_window("Last 24h", daily)))
    print("")
    print("**By project — last 7d**")
    print("\n".join(render_projects(weekly)))
    print("")
    print("**By Telegram topic — last 7d**")
    print("\n".join(render_topics(weekly)))
    print("")
    print("**By model — last 7d**")
    print("\n".join(render_models(weekly)))
    print("")
    stages = render_stages(weekly)
    if stages:
        print("**Script stages — last 7d**")
        print("\n".join(stages))
        print("")
    top = render_top_sessions(weekly)
    if top:
        print("**Top sessions — last 7d**")
        print("\n".join(top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
