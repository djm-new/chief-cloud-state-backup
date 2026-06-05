#!/usr/bin/env python3
"""Reusable starter for compact OpenRouter/Qwen podcast episode scoring.

Assumes an episodes SQLite table with columns similar to DJ's prototype:
id, show_name, ring, priority, title, link, published, summary, duration.
Adapt DB/OUTDIR paths as needed.
"""
import html
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone

import requests

BASE = Path(os.getenv("PODCAST_DIGEST_DIR", "/opt/data/podcast_digest"))
DB = BASE / "episodes.sqlite"
OUTDIR = BASE / "outputs"
MODEL = os.getenv("PODCAST_OSS_MODEL", "qwen/qwen3-235b-a22b")
BATCH_SIZE = int(os.getenv("PODCAST_SCORE_BATCH_SIZE", "10"))


def get_openrouter_key():
    val = os.getenv("OPENROUTER_API_KEY")
    if val:
        return val
    # Railway gateway quirk: terminal subprocess env can be stale after redeploy.
    try:
        for item in Path("/proc/1/environ").read_bytes().split(b"\0"):
            if item.startswith(b"OPENROUTER_API_KEY="):
                return item.split(b"=", 1)[1].decode()
    except Exception:
        pass
    return None


def clean(text, limit=1000):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(text))
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def load_episodes():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute("""
        select id, show_name, ring, priority, title, link, published, summary, duration
        from episodes
        order by published desc, show_name, title
    """)]


def score_batch(api_key, batch):
    system = """You are DJ Mauch's podcast episode filter. Score EPISODES, not shows.
Return ONLY valid JSON: {"results":[{"id":"...","score":0-100,"tier":"skip|scan|digest|listen","reason":"<=24 words","confidence":"low|medium|high"}]}.
Daily text digest should cast a wide net; weekly audio should be selective. Favor market reads, top investors/CEOs, AI platform/business-model insight, durable frameworks, and operator insight. Penalize generic AI hype, news recaps, politics, celebrity, generic VC fluff, and shallow promo."""
    payload = [{
        "id": e["id"],
        "show": e.get("show_name"),
        "ring": e.get("ring"),
        "source_priority": e.get("priority"),
        "title": clean(e.get("title"), 300),
        "published": e.get("published"),
        "duration_seconds": e.get("duration"),
        "summary": clean(e.get("summary"), 1000),
    } for e in batch]
    user = "/no_think\nScore these podcast episodes. Return only JSON.\n" + json.dumps(payload, ensure_ascii=False)
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://hermes-agent.local/podcast-digest",
            "X-Title": "Hermes Podcast Intelligence",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.1,
            "max_tokens": 1800,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
    return parsed.get("results", []), data.get("usage", {})


def main():
    api_key = get_openrouter_key()
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not found")
    episodes = load_episodes()
    scored = []
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for i in range(0, len(episodes), BATCH_SIZE):
        batch = episodes[i:i+BATCH_SIZE]
        results, usage = score_batch(api_key, batch)
        by_id = {str(r.get("id")): r for r in results}
        for e in batch:
            scored.append({**e, "qwen": by_id.get(e["id"], {"score": 0, "tier": "scan", "reason": "Model omitted this episode.", "confidence": "low"})})
        for k in usage_total:
            usage_total[k] += int(usage.get(k, 0) or 0)
        print(f"scored {min(i+BATCH_SIZE, len(episodes))}/{len(episodes)}")
        time.sleep(0.5)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    out = OUTDIR / f"{stamp}-qwen-episode-scores.json"
    out.write_text(json.dumps({"model": MODEL, "usage": usage_total, "episodes": scored}, indent=2, ensure_ascii=False))
    print(out)


if __name__ == "__main__":
    main()
