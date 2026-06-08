#!/usr/bin/env python3
"""Generate a calibrated daily podcast digest from a Qwen episode scoring JSON file.

Input: JSON produced by scripts/qwen_episode_score.py or the DJ prototype scorer.
Output: markdown digest with listen / digest / scan / skip sections.

This is a starter script: adapt source paths and calibration text as the podcast pipeline evolves.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, "/opt/data/scripts")
from openrouter_spend import openrouter_post_json

MODEL = os.getenv("PODCAST_OSS_MODEL", "qwen/qwen3-235b-a22b")
OUTDIR = Path(os.getenv("PODCAST_DIGEST_DIR", "/opt/data/podcast_digest")) / "outputs"


def clean(text, limit=900):
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scores_json")
    parser.add_argument("--window-start", default="")
    parser.add_argument("--window-end", default="")
    args = parser.parse_args()

    data = json.loads(Path(args.scores_json).read_text())
    episodes = []
    for e in data["episodes"]:
        q = e["qwen"]
        item = {
            "show": e.get("show_name"),
            "title": e.get("title"),
            "published": e.get("published"),
            "link": e.get("link") or "",
            "summary": clean(e.get("summary")),
            "qwen_score": q.get("score"),
            "qwen_tier": q.get("tier"),
            "qwen_reason": q.get("reason"),
            "confidence": q.get("confidence"),
        }
        episodes.append(item)

    system = """You write DJ Mauch's daily podcast intelligence digest.
Use only provided metadata and Qwen scores; do not invent details or links.
Calibration:
- Score/evaluate episodes, not shows.
- Daily digest casts a wider net and summarizes what was said.
- Listen is scarce: original audio likely worth DJ's time.
- Digest means summarize in text; original audio optional/unnecessary.
- Scan means maybe interesting / learn more.
- Skip means omit except filtered-noise note.
- Promote market shapers, top investors/CEOs, AI economics, platform/business model implications, capital allocation, durable frameworks.
- Penalize narrow AI infrastructure promo, technical research without business implication, vertical vendor stories, generic Bloomberg/news recaps, Elon/media narrative, consumer brand playbooks, politics.
- Stratechery best-of/Ben Thompson content is important; include if present.
Output markdown with no tables: title, window/funnel/cost placeholder, Executive read, Listen, Summarize in daily digest, Scan/maybe, Skipped noise, Calibration note."""
    user = (
        "/no_think\nGenerate today's digest for this 24h window. "
        f"Window start: {args.window_start}. Window end: {args.window_end}. "
        "Return only markdown. Episodes JSON:\n" + json.dumps(episodes, ensure_ascii=False)
    )
    data = openrouter_post_json(
        path="chat/completions",
        model=MODEL,
        title="Hermes Podcast Daily Digest",
        referer="https://hermes-agent.local/podcast-digest",
        timeout=180,
        payload={
            "model": MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
            "max_tokens": 5000,
        },
        source="cron",
        platform="cron",
        project_slug="podcast-intelligence-digest",
        workdir=str(Path(os.getenv("PODCAST_DIGEST_DIR", "/opt/data/podcast_digest"))),
        metadata={
            "workflow": "podcast-intelligence-digest",
            "stage": "daily_digest_render",
            "window_start": args.window_start,
            "window_end": args.window_end,
        },
    )
    content = data["choices"][0]["message"]["content"].strip()
    usage = data.get("usage", {})
    OUTDIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    out = OUTDIR / f"{stamp}-daily-podcast-digest-24h.md"
    out.write_text(f"<!-- model={MODEL}; usage={usage} -->\n" + content + "\n")
    print(out)
    print("usage", usage)


if __name__ == "__main__":
    main()
