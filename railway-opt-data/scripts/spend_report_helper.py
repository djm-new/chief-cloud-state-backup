#!/usr/bin/env python3
"""Unified Hermes spend/usage reporting.

Data sources (merged, deduped):
  1. /opt/data/state.db `sessions` — all agent sessions (telegram/cron/cli/api)
     with per-session tokens, model, billing mode, title.
  2. /opt/data/spend.db `llm_usage_events` — script-level LLM calls that are
     NOT agent sessions (podcast digest OpenRouter calls, etc.). Rows whose
     session_id exists in the sessions table are excluded to avoid
     double-counting.
  3. /opt/data/sessions/sessions.json — gateway session-key -> session_id map,
     used for Telegram topic attribution. Accumulated into a persistent
     snapshot so topic labels survive session resets.
  4. /opt/data/cron/jobs.json — cron job id -> human-readable job name.

Cost model:
  - `est_cost`: estimated dollar value at OpenRouter reference API rates,
    computed from token buckets (input/output/cache read/cache write). This
    applies even to subscription-included usage (openai-codex), so the report
    shows what the usage is *worth*, not just what was billed.
  - `billed_cost`: sum of actual_cost_usd when present (rare); otherwise the
    report labels the window as subscription-included / estimated.
  - `recorded_cost`: whatever cost the runtime recorded at call time
    (estimated_cost_usd), shown for transparency when nonzero.

Pricing is cached in /opt/data/spend-monitor/pricing_cache.json (7-day TTL).
Works both inside the Hermes venv (uses agent.usage_pricing) and standalone
(direct OpenRouter /models fetch with key from env or /proc/1/environ).
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

STATE_DB = Path("/opt/data/state.db")
SPEND_DB = Path("/opt/data/spend.db")
SESSIONS_INDEX = Path("/opt/data/sessions/sessions.json")
JOBS_JSON = Path("/opt/data/cron/jobs.json")
MONITOR_DIR = Path("/opt/data/spend-monitor")
TOPIC_SNAPSHOT = MONITOR_DIR / "session_topics.json"
PRICING_CACHE = MONITOR_DIR / "pricing_cache.json"
PRICING_TTL_SECONDS = 7 * 24 * 3600

# Best-effort Telegram topic id -> name map for the Chief group.
# Confident: 1 (General), 4 (Briefings), 5 (Alerts), 6 (Daily Brain Dump)
# from cron delivery targets; 7 (Coding) from model override + usage.
# 3/8 inferred from session titles (Archive vs ad-hoc).
TOPIC_NAMES = {
    "1": "General/home",
    "3": "Archive/Old Chief",
    "4": "Briefings",
    "5": "Alerts",
    "6": "Daily Brain Dump",
    "7": "Coding",
    "8": "General (ad-hoc/conversational)",
}

CHIEF_CHAT_ID = "-1003956828149"


# ---------------------------------------------------------------------------
# Pricing (OpenRouter reference rates, cached)
# ---------------------------------------------------------------------------

def _openrouter_key() -> str | None:
    key = os.getenv("OPENROUTER_API_KEY")
    if key:
        return key
    try:
        for item in Path("/proc/1/environ").read_bytes().split(b"\0"):
            if item.startswith(b"OPENROUTER_API_KEY="):
                return item.split(b"=", 1)[1].decode()
    except Exception:
        pass
    return None


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _save_json(path: Path, data) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def _pricing_via_hermes(model: str) -> dict[str, float | None] | None:
    try:
        from agent.usage_pricing import get_pricing_entry  # type: ignore

        entry = get_pricing_entry(model, provider="openrouter", api_key=_openrouter_key())
        if not entry:
            return None
        return {
            "in": float(entry.input_cost_per_million) if entry.input_cost_per_million is not None else None,
            "out": float(entry.output_cost_per_million) if entry.output_cost_per_million is not None else None,
            "cache_r": float(entry.cache_read_cost_per_million) if entry.cache_read_cost_per_million is not None else None,
            "cache_w": float(entry.cache_write_cost_per_million) if entry.cache_write_cost_per_million is not None else None,
        }
    except Exception:
        return None


def _pricing_via_http(models: set[str]) -> dict[str, dict[str, float | None]]:
    key = _openrouter_key()
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except Exception:
        return {}
    out: dict[str, dict[str, float | None]] = {}
    wanted = {m.lower() for m in models}
    for item in payload.get("data", []):
        mid = str(item.get("id") or "")
        short = mid.split("/")[-1]
        if mid.lower() not in wanted and short.lower() not in wanted:
            continue
        pricing = item.get("pricing") or {}

        def per_million(field: str) -> float | None:
            try:
                v = float(pricing.get(field) or 0)
                return v * 1_000_000 if v else None
            except Exception:
                return None

        entry = {
            "in": per_million("prompt"),
            "out": per_million("completion"),
            "cache_r": per_million("input_cache_read"),
            "cache_w": per_million("input_cache_write"),
        }
        for name in models:
            if name.lower() in (mid.lower(), short.lower()):
                out[name] = entry
    return out


def _pricing_candidates(model: str) -> list[str]:
    """Generate lookup candidates for a model name.

    Handles vendor prefixes and OpenRouter's dotted-version ids, e.g.
    'claude-sonnet-4-6' -> 'anthropic/claude-sonnet-4.6'.
    """
    candidates = [model]
    base = model.split("/", 1)[1] if "/" in model else model
    # dotted version variant: trailing '-N-M' -> '-N.M' (e.g. sonnet-4-6 -> sonnet-4.6)
    dotted = re.sub(r"(\d+)-(\d+)$", r"\1.\2", base)
    vendor = None
    if base.startswith("claude"):
        vendor = "anthropic"
    elif base.startswith(("gpt", "o1", "o3", "o4")):
        vendor = "openai"
    elif base.startswith("kimi"):
        vendor = "moonshotai"
    elif base.startswith("qwen"):
        vendor = "qwen"
    if vendor:
        candidates.append(f"{vendor}/{base}")
        if dotted != base:
            candidates.append(f"{vendor}/{dotted}")
    if dotted != base:
        candidates.append(dotted)
    # de-dupe, preserve order
    seen: set[str] = set()
    out = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def get_reference_pricing(models: set[str]) -> dict[str, dict[str, float | None]]:
    """Return {model: {in,out,cache_r,cache_w}} per-million USD, cached 7d."""
    cache = _load_json(PRICING_CACHE, {})
    now = time.time()
    result: dict[str, dict[str, float | None]] = {}
    missing: set[str] = set()
    for model in models:
        entry = cache.get(model)
        if entry and now - float(entry.get("fetched_at", 0)) < PRICING_TTL_SECONDS:
            result[model] = entry["pricing"]
        else:
            missing.add(model)
    for model in sorted(missing):
        for candidate in _pricing_candidates(model):
            pricing = _pricing_via_hermes(candidate)
            if pricing:
                result[model] = pricing
                cache[model] = {"fetched_at": now, "pricing": pricing, "resolved_as": candidate}
                break
    still_missing = {m for m in missing if m not in result}
    if still_missing:
        # HTTP fallback: fetch the full model list once, match all candidates.
        all_candidates: dict[str, str] = {}  # candidate -> original model
        for model in still_missing:
            for candidate in _pricing_candidates(model):
                all_candidates[candidate] = model
        http_results = _pricing_via_http(set(all_candidates))
        for candidate, pricing in http_results.items():
            original = all_candidates.get(candidate)
            if original and original not in result:
                result[original] = pricing
                cache[original] = {"fetched_at": now, "pricing": pricing, "resolved_as": candidate}
    _save_json(PRICING_CACHE, cache)
    return result


def estimate_cost(model: str, pricing: dict, input_tokens: int, output_tokens: int,
                  cache_read: int, cache_write: int) -> float | None:
    entry = pricing.get(model)
    if not entry:
        return None
    cost = 0.0
    priced_any = False
    if entry.get("in") is not None and input_tokens:
        cost += input_tokens * entry["in"] / 1_000_000
        priced_any = True
    if entry.get("out") is not None and output_tokens:
        cost += output_tokens * entry["out"] / 1_000_000
        priced_any = True
    if entry.get("cache_r") is not None and cache_read:
        cost += cache_read * entry["cache_r"] / 1_000_000
        priced_any = True
    if entry.get("cache_w") is not None and cache_write:
        cost += cache_write * entry["cache_w"] / 1_000_000
        priced_any = True
    if not priced_any and (input_tokens or output_tokens):
        return None
    return cost


# ---------------------------------------------------------------------------
# Attribution helpers
# ---------------------------------------------------------------------------

def _cron_job_names() -> dict[str, str]:
    data = _load_json(JOBS_JSON, {})
    jobs = data.get("jobs") if isinstance(data, dict) else data
    out: dict[str, str] = {}
    if isinstance(jobs, list):
        for job in jobs:
            if not isinstance(job, dict):
                continue
            jid = job.get("id") or job.get("job_id")
            if jid:
                out[str(jid)] = str(job.get("name") or jid)
    return out


def _session_topic_map() -> dict[str, str]:
    """session_id -> Telegram topic label, accumulated across runs.

    Seeds from the gateway sessions.json index, then propagates labels through
    the session graph: parent_session_id links (both directions) and
    session_reset pairs (a session ending with end_reason='session_reset' at
    ~the same timestamp another telegram session starts is the same topic
    continuing under a new id).
    """
    snapshot: dict[str, str] = _load_json(TOPIC_SNAPSHOT, {})
    index = _load_json(SESSIONS_INDEX, {})
    changed = False
    for key, entry in index.items():
        if not isinstance(entry, dict):
            continue
        sid = entry.get("session_id")
        if not sid or sid in snapshot:
            continue
        # key shape: agent:main:telegram:group:<chat_id>:<topic_or_user>
        m = re.match(r"agent:[^:]+:telegram:(group|dm|thread|channel):([^:]+):(.+)$", key)
        if not m:
            continue
        kind, chat_id, suffix = m.group(1), m.group(2), m.group(3)
        if kind == "dm":
            snapshot[sid] = "Telegram DM"
            changed = True
        elif chat_id == CHIEF_CHAT_ID:
            label = TOPIC_NAMES.get(suffix)
            snapshot[sid] = label or f"Chief Group topic {suffix}"
            changed = True
        else:
            snapshot[sid] = f"Telegram chat {chat_id}"
            changed = True

    # Propagate through the telegram session graph.
    try:
        con = sqlite3.connect(STATE_DB)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(
            "SELECT id, parent_session_id, started_at, ended_at, end_reason "
            "FROM sessions WHERE source='telegram'"
        ).fetchall()]
        con.close()
    except Exception:
        rows = []

    if rows:
        info = {r["id"]: r for r in rows}
        # Build adjacency: parent links (both directions) + reset-time pairs.
        neighbors: dict[str, set[str]] = defaultdict(set)
        by_start = sorted((r for r in rows if r.get("started_at")), key=lambda r: r["started_at"])
        for r in rows:
            parent = r.get("parent_session_id")
            if parent and parent in info:
                neighbors[r["id"]].add(parent)
                neighbors[parent].add(r["id"])
        # Reset pairs: a session whose end_reason is session_reset and whose
        # ended_at is within a few seconds of another session's started_at.
        ended = [r for r in rows if r.get("ended_at") and r.get("end_reason") == "session_reset"]
        for e in ended:
            for s in by_start:
                if s["id"] == e["id"]:
                    continue
                if abs(float(s["started_at"]) - float(e["ended_at"])) <= 5.0:
                    neighbors[e["id"]].add(s["id"])
                    neighbors[s["id"]].add(e["id"])
        # BFS from every labeled node.
        queue = [sid for sid in snapshot if sid in info]
        visited = set(queue)
        while queue:
            current = queue.pop(0)
            label = snapshot[current]
            for nxt in neighbors.get(current, ()):
                if nxt in visited:
                    continue
                visited.add(nxt)
                if nxt not in snapshot:
                    snapshot[nxt] = label
                    changed = True
                queue.append(nxt)

    if changed:
        _save_json(TOPIC_SNAPSHOT, snapshot)
    return snapshot


def _topic_from_gateway_key(key: str) -> str | None:
    m = re.match(r"agent:[^:]+:telegram:(?:group|thread|channel):([^:]+):(.+)$", key or "")
    if not m:
        return None
    chat_id, suffix = m.group(1), m.group(2)
    if chat_id == CHIEF_CHAT_ID:
        return TOPIC_NAMES.get(suffix) or f"Chief Group topic {suffix}"
    return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_sessions(cutoff_epoch: float) -> list[dict[str, Any]]:
    if not STATE_DB.exists():
        return []
    con = sqlite3.connect(STATE_DB)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT id, source, model, title, started_at,
                   COALESCE(input_tokens,0) input_tokens,
                   COALESCE(output_tokens,0) output_tokens,
                   COALESCE(cache_read_tokens,0) cache_read_tokens,
                   COALESCE(cache_write_tokens,0) cache_write_tokens,
                   COALESCE(reasoning_tokens,0) reasoning_tokens,
                   billing_provider, billing_mode,
                   COALESCE(estimated_cost_usd,0) estimated_cost_usd,
                   actual_cost_usd, cost_status
            FROM sessions
            WHERE started_at >= ?
            """,
            (cutoff_epoch,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def _load_ledger_events(cutoff_epoch: float, known_session_ids: set[str]) -> list[dict[str, Any]]:
    if not SPEND_DB.exists():
        return []
    con = sqlite3.connect(SPEND_DB)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT session_id, provider, model, source, platform, channel_label,
                   gateway_session_key, project_slug, workdir,
                   COALESCE(input_tokens,0) input_tokens,
                   COALESCE(output_tokens,0) output_tokens,
                   COALESCE(cache_read_tokens,0) cache_read_tokens,
                   COALESCE(cache_write_tokens,0) cache_write_tokens,
                   COALESCE(total_tokens,0) total_tokens,
                   estimated_cost_usd, cost_status, metadata_json
            FROM llm_usage_events
            WHERE created_at >= ?
            """,
            (cutoff_epoch,),
        ).fetchall()
    finally:
        con.close()
    out = []
    for r in rows:
        d = dict(r)
        sid = (d.get("session_id") or "").strip()
        if sid and sid in known_session_ids:
            continue  # already counted via the sessions table
        meta = _load_json_str(d.get("metadata_json"))
        d["workflow"] = meta.get("workflow") or ""
        d["stage"] = meta.get("stage") or ""
        out.append(d)
    return out


def _load_json_str(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def _new_bucket() -> dict[str, Any]:
    return {
        "tokens": 0, "input": 0, "output": 0, "cache_r": 0, "cache_w": 0,
        "est_cost": 0.0, "unpriced_tokens": 0, "sessions": 0, "events": 0,
        "models": defaultdict(lambda: {"tokens": 0, "est_cost": 0.0}),
    }


def _add_tokens(bucket: dict, model: str, input_t: int, output_t: int, cache_r: int, cache_w: int,
                est: float | None) -> None:
    total = input_t + output_t + cache_r + cache_w
    bucket["tokens"] += total
    bucket["input"] += input_t
    bucket["output"] += output_t
    bucket["cache_r"] += cache_r
    bucket["cache_w"] += cache_w
    if est is None:
        bucket["unpriced_tokens"] += total
    else:
        bucket["est_cost"] += est
        bucket["models"][model]["est_cost"] += est
    bucket["models"][model]["tokens"] += total


def build_report(days: int) -> dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()

    sessions = _load_sessions(cutoff)
    session_ids = {s["id"] for s in sessions}
    events = _load_ledger_events(cutoff, session_ids)
    topic_map = _session_topic_map()
    job_names = _cron_job_names()

    # Collect all models for pricing lookup.
    models = {s.get("model") or "unknown" for s in sessions}
    models |= {e.get("model") or "unknown" for e in events}
    models.discard("unknown")
    pricing = get_reference_pricing(models) if models else {}

    overview = {
        "sessions": 0, "events": 0,
        "total_tokens": 0, "input_tokens": 0, "output_tokens": 0,
        "cache_read_tokens": 0, "cache_write_tokens": 0,
        "est_cost": 0.0, "unpriced_tokens": 0,
        "recorded_cost": 0.0, "billed_cost": 0.0, "has_billed": False,
        "subscription_sessions": 0, "priced_sessions": 0,
    }
    projects: dict[str, dict[str, Any]] = defaultdict(_new_bucket)
    topics: dict[str, dict[str, Any]] = defaultdict(_new_bucket)
    models_out: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "tokens": 0, "est_cost": 0.0, "sessions": 0, "events": 0,
        "provider": "", "billing_modes": set(),
    })
    top_sessions: list[dict[str, Any]] = []
    stages: dict[str, dict[str, Any]] = defaultdict(_new_bucket)

    for s in sessions:
        model = s.get("model") or "unknown"
        it, ot = int(s["input_tokens"]), int(s["output_tokens"])
        cr, cw = int(s["cache_read_tokens"]), int(s["cache_write_tokens"])
        est = estimate_cost(model, pricing, it, ot, cr, cw)
        recorded = float(s.get("estimated_cost_usd") or 0)
        billing_mode = s.get("billing_mode") or ""
        provider = s.get("billing_provider") or ""

        total = it + ot + cr + cw
        overview["sessions"] += 1
        overview["total_tokens"] += total
        overview["input_tokens"] += it
        overview["output_tokens"] += ot
        overview["cache_read_tokens"] += cr
        overview["cache_write_tokens"] += cw
        overview["recorded_cost"] += recorded
        if est is None:
            overview["unpriced_tokens"] += total
        else:
            overview["est_cost"] += est
        if billing_mode == "subscription_included":
            overview["subscription_sessions"] += 1
        if s.get("actual_cost_usd") is not None:
            overview["billed_cost"] += float(s["actual_cost_usd"])
            overview["has_billed"] = True

        # Project attribution
        src = s.get("source") or "unknown"
        if src == "cron":
            m = re.match(r"cron_([0-9a-f]+)_", s["id"])
            job_name = job_names.get(m.group(1), f"cron job {m.group(1)}") if m else "cron (other)"
            project = f"Cron: {job_name}"
        elif src == "telegram":
            project = f"Telegram: {topic_map.get(s['id'], 'Chief Group (unmapped)')}"
        elif src == "cli":
            project = "CLI"
        elif src == "api":
            project = "API"
        else:
            project = src.capitalize()
        projects[project]["sessions"] += 1
        _add_tokens(projects[project], model, it, ot, cr, cw, est)

        # Telegram topic attribution
        if src == "telegram":
            topic = topic_map.get(s["id"], "Chief Group (unmapped)")
            topics[topic]["sessions"] += 1
            _add_tokens(topics[topic], model, it, ot, cr, cw, est)

        mo = models_out[model]
        mo["tokens"] += total
        mo["sessions"] += 1
        mo["provider"] = provider or mo["provider"]
        if billing_mode:
            mo["billing_modes"].add(billing_mode)
        if est is not None:
            mo["est_cost"] += est

        top_sessions.append({
            "id": s["id"], "title": s.get("title") or "",
            "model": model, "source": src,
            "tokens": total, "est_cost": est,
        })

    for e in events:
        model = e.get("model") or "unknown"
        it, ot = int(e["input_tokens"]), int(e["output_tokens"])
        cr, cw = int(e["cache_read_tokens"]), int(e["cache_write_tokens"])
        recorded = float(e.get("estimated_cost_usd") or 0)
        est = estimate_cost(model, pricing, it, ot, cr, cw)
        if (est is None or est == 0.0) and recorded > 0:
            est = recorded  # ledger estimate (provider_models_api) is the best number

        total = it + ot + cr + cw or int(e.get("total_tokens") or 0)
        overview["events"] += 1
        overview["total_tokens"] += total
        overview["input_tokens"] += it
        overview["output_tokens"] += ot
        overview["cache_read_tokens"] += cr
        overview["cache_write_tokens"] += cw
        overview["recorded_cost"] += recorded
        if est is None:
            overview["unpriced_tokens"] += total
        else:
            overview["est_cost"] += est

        workflow = e.get("workflow") or e.get("project_slug") or ""
        if workflow:
            project = f"Script: {workflow}"
        elif e.get("channel_label"):
            project = str(e["channel_label"])
        else:
            project = f"Script: {e.get('platform') or e.get('source') or 'other'}"
        projects[project]["events"] += 1
        _add_tokens(projects[project], model, it, ot, cr, cw, est)

        # Telegram topics from gateway session keys (historical ledger rows)
        topic = _topic_from_gateway_key(e.get("gateway_session_key") or "")
        if topic:
            topics[topic]["events"] += 1
            _add_tokens(topics[topic], model, it, ot, cr, cw, est)

        if workflow and e.get("stage"):
            stage_key = f"{workflow} — {e['stage']}"
            stages[stage_key]["events"] += 1
            _add_tokens(stages[stage_key], model, it, ot, cr, cw, est)

        mo = models_out[model]
        mo["tokens"] += total
        mo["events"] += 1
        mo["provider"] = (e.get("provider") or "") or mo["provider"]
        if est is not None:
            mo["est_cost"] += est

    def pack(bucket: dict) -> dict[str, Any]:
        top_models = sorted(bucket["models"].items(), key=lambda kv: kv[1]["est_cost"], reverse=True)[:2]
        return {
            "tokens": bucket["tokens"], "est_cost": bucket["est_cost"],
            "sessions": bucket["sessions"], "events": bucket["events"],
            "unpriced_tokens": bucket["unpriced_tokens"],
            "top_models": [{"model": m, "tokens": v["tokens"], "est_cost": v["est_cost"]} for m, v in top_models],
        }

    projects_out = [
        {"project": name, **pack(b)}
        for name, b in sorted(projects.items(), key=lambda kv: kv[1]["est_cost"], reverse=True)
    ]
    topics_out = [
        {"topic": name, **pack(b)}
        for name, b in sorted(topics.items(), key=lambda kv: kv[1]["est_cost"], reverse=True)
    ]
    stages_out = [
        {"stage": name, **pack(b)}
        for name, b in sorted(stages.items(), key=lambda kv: kv[1]["est_cost"], reverse=True)
    ]
    models_list = [
        {
            "model": model,
            "provider": v["provider"],
            "tokens": v["tokens"],
            "est_cost": v["est_cost"],
            "sessions": v["sessions"],
            "events": v["events"],
            "billing_modes": sorted(v["billing_modes"]),
        }
        for model, v in sorted(models_out.items(), key=lambda kv: kv[1]["est_cost"], reverse=True)
    ]
    top_sessions.sort(key=lambda s: (s["est_cost"] or 0, s["tokens"]), reverse=True)

    return {
        "days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": overview,
        "projects": projects_out,
        "telegram_topics": topics_out,
        "models": models_list,
        "stages": stages_out,
        "top_sessions": top_sessions[:8],
    }


def summarize_spend(days: int) -> dict[str, Any]:
    """Backwards-compatible entry point used by the briefing scripts."""
    return build_report(days)


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(json.dumps(build_report(days), indent=2, default=str))
