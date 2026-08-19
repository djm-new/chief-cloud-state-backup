#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from spend_report_helper import build_report

ET = ZoneInfo("America/New_York")
STATE_DIR = Path(os.getenv("HERMES_HOME", "").strip() or (Path.home() / ".hermes")) / "spend-monitor"
LAST_SENT_FILE = STATE_DIR / "last_daily_briefing_et_date.txt"


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


def clean_label(text: str | None) -> str:
    text = (text or "").strip()
    if not text:
        return "Untitled work"
    for prefix in ("Telegram: ", "Cron: ", "Script: "):
        if text.startswith(prefix):
            text = text[len(prefix):]
    if text.startswith("Chief Group topic "):
        text = "Unlabeled Chief Group thread"
    return text


def source_label(item: dict) -> str:
    project = item.get("project") or item.get("source") or ""
    source = item.get("source") or ""
    if project.startswith("Telegram: "):
        return clean_label(project)
    if project.startswith("Cron: "):
        return "scheduled job"
    if project.startswith("Script: "):
        return "script"
    return source or clean_label(project)


def render_summary(label: str, report: dict) -> list[str]:
    o = report.get("overview", {}) or {}
    lines = [f"**{label}**"]
    lines.append(f"- Estimated API-rate value: {usd(o.get('est_cost'))}")
    lines.append(f"- Tokens: {num(o.get('total_tokens'))} ({tokens_compact(o.get('input_tokens'))} in · {tokens_compact(o.get('output_tokens'))} out · {tokens_compact(o.get('cache_read_tokens'))} cache)")
    if o.get("has_billed"):
        lines.append(f"- Billed spend: {usd(o.get('billed_cost'))}")
    else:
        lines.append("- Billed spend: unavailable; local value is API-rate estimate, and Codex usage is subscription-included")
    if o.get("unpriced_tokens"):
        lines.append(f"- Pricing gap: {num(o.get('unpriced_tokens'))} unpriced tokens")
    return lines


def render_work(report: dict, max_rows: int = 10) -> list[str]:
    rows = [r for r in (report.get("work_items") or report.get("top_sessions") or []) if r.get("tokens")]
    if not rows:
        return ["- No usage recorded in this window."]
    lines = []
    for row in rows[:max_rows]:
        title = clean_label(row.get("title") or row.get("project") or row.get("id"))
        location = source_label(row)
        model = row.get("model") or "unknown model"
        cost = usd(row.get("est_cost")) if row.get("est_cost") is not None else "unpriced"
        line = f"- **{title}** — ~{cost}, {tokens_compact(row.get('tokens'))} tokens"
        details = []
        if location:
            details.append(location)
        if model:
            details.append(model)
        if row.get("billing_mode") == "subscription_included":
            details.append("subscription-included")
        if details:
            line += f" ({' · '.join(details)})"
        lines.append(line)
    return lines


def render_project_rollup(report: dict, max_rows: int = 6) -> list[str]:
    rows = [r for r in (report.get("projects", []) or []) if r.get("tokens")]
    if not rows:
        return ["- No project rollup available."]
    lines = []
    for row in rows[:max_rows]:
        project = clean_label(row.get("project"))
        lines.append(f"- {project}: ~{usd(row.get('est_cost'))}, {tokens_compact(row.get('tokens'))} tokens")
    return lines


def render_models(report: dict, max_rows: int = 5) -> list[str]:
    rows = [r for r in (report.get("models", []) or []) if r.get("tokens")]
    if not rows:
        return ["- No model usage."]
    lines = []
    for row in rows[:max_rows]:
        flags = []
        modes = row.get("billing_modes") or []
        if "subscription_included" in modes:
            flags.append("included")
        if row.get("provider"):
            flags.append(row.get("provider"))
        suffix = f" ({' · '.join(flags)})" if flags else ""
        lines.append(f"- {row.get('model')}: ~{usd(row.get('est_cost'))}, {tokens_compact(row.get('tokens'))} tokens{suffix}")
    return lines


def should_emit(now_et: datetime) -> bool:
    if os.getenv("HERMES_SPEND_REPORT_FORCE") == "1":
        return True
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

    daily = build_report(1)
    weekly = build_report(7)

    print("## Hermes Spend Briefing")
    print(f"As of: {now_et.strftime('%a %b %-d, %-I:%M %p ET')}")
    print("")
    print("**What cost money — last 24h**")
    print("\n".join(render_work(daily, max_rows=8)))
    print("")
    print("\n".join(render_summary("Last 24h totals", daily)))
    print("")
    print("**What cost money — last 7d**")
    print("\n".join(render_work(weekly, max_rows=12)))
    print("")
    print("\n".join(render_summary("Last 7d totals", weekly)))
    print("")
    print("**Where the spend clustered — last 7d**")
    print("\n".join(render_project_rollup(weekly)))
    print("")
    print("**Model mix — last 7d**")
    print("\n".join(render_models(weekly)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
