#!/usr/bin/env python3
"""Generate DJ Mauch's weekly original podcast-of-podcasts audio.

Workflow:
- Read the latest daily podcast digests.
- Pick the strongest episodes of the week.
- Fetch rich episode-page text when available.
- Ask OpenRouter to write an original two-host weekly podcast script.
- Synthesize the script into chunked TTS audio using Hermes' configured TTS.
- Concatenate the chunks into a single Telegram-ready .ogg file.

This is intentionally a production-ish script: it can run standalone and it
writes durable artifacts to /opt/data/podcast_digest/outputs/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = Path("/opt/data/podcast_digest")
OUTDIR = BASE / "outputs"
DAILY_GLOB = "*daily-podcast-digest-24h.md"
WEEKLY_MODEL = os.getenv("PODCAST_WEEKLY_MODEL", "qwen/qwen3-235b-a22b")

sys.path.insert(0, "/opt/data/scripts")
sys.path.insert(0, "/opt/hermes")

from openrouter_spend import openrouter_post_json  # noqa: E402
from tools.tts_tool import text_to_speech_tool  # noqa: E402


def clean(text: str, limit: int = 1800) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[:limit]


def latest_daily_outputs(limit: int = 7) -> list[Path]:
    files = sorted(OUTDIR.glob(DAILY_GLOB), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def parse_daily_digest(path: Path) -> list[dict[str, Any]]:
    """Extract candidate episodes from one daily digest markdown file."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    items: list[dict[str, Any]] = []
    i = 0
    current_section = None
    section_rank = {"Listen": 3, "Summarize in Digest": 2, "Scan / Maybe": 1, "Scan / maybe": 1}
    while i < len(lines):
        line = lines[i].strip()
        msec = re.match(r"^##\s+(.+)$", line)
        if msec:
            current_section = msec.group(1).strip()
            i += 1
            continue
        mep = re.match(r"^###\s+\*\*(.+?)\s+—\s+(.+?)\*\*$", line)
        if not mep:
            mep = re.match(r"^###\s+(.+?)\s+—\s+(.+)$", line)
        if mep:
            show = clean(mep.group(1), 120)
            episode = clean(mep.group(2), 240)
            block_lines = []
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("### ") or nxt.startswith("## "):
                    break
                block_lines.append(nxt)
                i += 1
            block = "\n".join(block_lines)
            rec = ""
            link = ""
            what = ""
            why = ""
            for bl in block_lines:
                if "Recommendation" in bl:
                    rec = bl.split("Recommendation")[-1].strip(" :-*")
                if "Link" in bl:
                    m = re.search(r"\((https?://[^)]+)\)", bl)
                    if m:
                        link = m.group(1)
                if bl.lower().startswith("- **what was said**:"):
                    what = bl.split(":", 1)[-1].strip()
                if bl.lower().startswith("- **why dj should care**:"):
                    why = bl.split(":", 1)[-1].strip()
            items.append(
                {
                    "date_file": path.name,
                    "show": show,
                    "episode": episode,
                    "section": current_section or "",
                    "section_rank": section_rank.get(current_section or "", 0),
                    "recommendation": rec.lower(),
                    "link": link,
                    "what": what,
                    "why": why,
                    "raw_block": block,
                }
            )
            continue
        i += 1
    return items


def dedupe_rank(items: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
    """Deduplicate by normalized show+episode and rank by section + recency frequency."""
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        key = re.sub(r"\s+", " ", f"{item['show']} — {item['episode']}".lower()).strip()
        buckets[key].append(item)
    scored = []
    for key, group in buckets.items():
        best = max(group, key=lambda x: (x.get("section_rank", 0), len(x.get("what", "")), len(x.get("why", ""))))
        score = sum(max(1, x.get("section_rank", 0)) for x in group)
        scored.append((score, len(group), best))
    scored.sort(key=lambda t: (t[0], t[1], t[2].get("section_rank", 0)), reverse=True)
    return [t[2] for t in scored[:top_n]]


def fetch_page_excerpt(url: str, limit: int = 1600) -> str:
    if not url:
        return ""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 Hermes Podcast Digest"})
    try:
        with urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, OSError):
        return ""
    # Crude but durable extraction: prefer meta description, otherwise strip tags
    # from the page body. Episode pages usually include enough structured text.
    meta_desc = re.search(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if meta_desc:
        return clean(meta_desc.group(1), limit)
    html = re.sub(r'(?is)<(script|style|noscript|svg).*?>.*?</\1>', ' ', html)
    html = re.sub(r'(?is)<header.*?>.*?</header>', ' ', html)
    html = re.sub(r'(?is)<footer.*?>.*?</footer>', ' ', html)
    html = re.sub(r'(?is)<nav.*?>.*?</nav>', ' ', html)
    html = re.sub(r'(?is)<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', html).strip()
    return clean(text, limit)


def build_source_briefs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    briefs = []
    for item in items:
        excerpt = fetch_page_excerpt(item.get("link", ""))
        briefs.append(
            {
                "show": item["show"],
                "episode": item["episode"],
                "link": item.get("link", ""),
                "section": item.get("section", ""),
                "what": item.get("what", ""),
                "why": item.get("why", ""),
                "page_excerpt": excerpt,
                "source_file": item.get("date_file", ""),
            }
        )
    return briefs


def draft_weekly_script(source_briefs: list[dict[str, Any]], window_days: int) -> tuple[str, dict[str, Any]]:
    system = """You write an original weekly podcast-of-podcasts for DJ Mauch.
Do not write a summary list. Write a lively two-host conversation.
Use the supplied briefs as source material only; do not invent specific facts.
The angle should be: AI is shifting from model novelty to industrial plumbing, capital allocation, governance, and operating leverage.
Tailor the relevance to DJ's taste: CEOs, top investors, AI leaders, platform strategy, software economics, durable frameworks.
Make it sound like a real show, not bullet points."""
    user = (
        "/no_think\n" 
        f"Create the weekly original podcast script for the last {window_days} days. "
        "Use speaker labels exactly as MAYA: and SAM:. "
        "Target length is about 10-14 minutes spoken. "
        "Start with a cold open. Include a closing synthesis with what DJ should watch next week. "
        "Source briefs:\n"
        + json.dumps(source_briefs, indent=2, ensure_ascii=False)
    )
    resp = openrouter_post_json(
        path="chat/completions",
        model=WEEKLY_MODEL,
        title="Hermes Weekly Podcast of Podcasts Script",
        referer="https://hermes-agent.local/podcast-digest",
        timeout=240,
        payload={
            "model": WEEKLY_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.35,
            "max_tokens": 4000,
        },
        source="cron",
        platform="cron",
        project_slug="podcast-intelligence-digest",
        workdir=str(BASE),
        metadata={
            "workflow": "podcast-intelligence-digest",
            "stage": "weekly_audio_script",
            "window_days": window_days,
            "source_count": len(source_briefs),
        },
    )
    script = resp["choices"][0]["message"]["content"].strip()
    usage = resp.get("usage", {})
    return script, usage


def clean_for_tts(script: str) -> str:
    text = script
    text = re.sub(r"^\s*(MAYA|SAM):\s*", "", text, flags=re.M)
    text = text.replace("**", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def chunk_text(text: str, target_chars: int = 2800) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for p in paras:
        candidate = f"{current}\n\n{p}".strip() if current else p
        if current and len(candidate) > target_chars:
            chunks.append(current.strip())
            current = p
        else:
            current = candidate
    if current:
        chunks.append(current.strip())
    return chunks


def synthesize_audio(chunks: list[str], output_base: Path) -> Path:
    audio_paths: list[Path] = []
    for idx, chunk in enumerate(chunks, 1):
        out = output_base.with_name(f"{output_base.stem}-chunk-{idx}.ogg")
        result = text_to_speech_tool(chunk, output_path=str(out))
        try:
            payload = json.loads(result) if isinstance(result, str) else result
        except Exception:
            payload = {"success": False, "error": f"Unexpected TTS result: {result!r}"}
        if not payload.get("success", True):
            raise RuntimeError(f"TTS failed for chunk {idx}: {payload}")
        file_path = Path(payload.get("file_path") or out)
        if not file_path.exists():
            raise RuntimeError(f"TTS chunk missing: {file_path}")
        audio_paths.append(file_path)
    list_path = output_base.with_suffix(".concat.txt")
    list_path.write_text("".join(f"file '{p}'\n" for p in audio_paths), encoding="utf-8")

    # Re-encode the concatenated stream into a single Telegram-friendly OGG Opus file.
    final_ogg = output_base.with_suffix(".ogg")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-acodec", "libopus", "-ac", "1", "-b:a", "64k", "-vbr", "off",
        str(final_ogg),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {res.stderr[-500:]}")

    if not final_ogg.exists() or final_ogg.stat().st_size <= 0:
        raise RuntimeError(f"Final audio not created: {final_ogg}")
    return final_ogg


def save_artifacts(base_name: str, script: str, tts_text: str, source_briefs: list[dict[str, Any]], usage: dict[str, Any], model: str) -> dict[str, Path]:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d_%H%M")
    outdir = OUTDIR
    outdir.mkdir(parents=True, exist_ok=True)
    script_path = outdir / f"{stamp}-{base_name}.md"
    tts_path = outdir / f"{stamp}-{base_name}-tts.txt"
    sources_path = outdir / f"{stamp}-{base_name}-sources.json"
    meta_path = outdir / f"{stamp}-{base_name}-meta.json"
    script_path.write_text(script + "\n", encoding="utf-8")
    tts_path.write_text(tts_text + "\n", encoding="utf-8")
    sources_path.write_text(json.dumps(source_briefs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta_path.write_text(
        json.dumps({"model": model, "usage": usage, "created_at_utc": stamp}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"script": script_path, "tts": tts_path, "sources": sources_path, "meta": meta_path}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if os.getenv("PODCAST_WEEKLY_FORCE_RUN", "0") != "1":
        try:
            from zoneinfo import ZoneInfo
            et_hour = dt.datetime.now(ZoneInfo("America/New_York")).hour
        except Exception:
            et_hour = dt.datetime.utcnow().hour
        if et_hour != 17:
            return 0

    digest_files = latest_daily_outputs(limit=args.days)
    if not digest_files:
        raise SystemExit("No daily podcast digest files found")

    all_items: list[dict[str, Any]] = []
    for path in digest_files:
        all_items.extend(parse_daily_digest(path))
    # Prefer high-signal sections; skip obvious noise.
    filtered = [
        i for i in all_items
        if i.get("section_rank", 0) > 0 and "skip" not in i.get("recommendation", "")
    ]
    picked = dedupe_rank(filtered, top_n=args.top_n)
    if not picked:
        raise SystemExit("No qualifying episodes found in recent digests")

    source_briefs = build_source_briefs(picked)
    script, usage = draft_weekly_script(source_briefs, window_days=args.days)
    artifacts = save_artifacts(
        base_name="weekly-podcast-of-podcasts",
        script=script,
        tts_text=clean_for_tts(script),
        source_briefs=source_briefs,
        usage=usage,
        model=WEEKLY_MODEL,
    )
    print(f"Wrote script: {artifacts['script']}")
    print(f"Wrote sources: {artifacts['sources']}")
    print(f"Wrote meta: {artifacts['meta']}")
    print(f"Weekly script model usage: {usage}")

    if args.dry_run:
        print(script)
        return 0

    tts_text = artifacts["tts"].read_text(encoding="utf-8")
    chunks = chunk_text(tts_text, target_chars=2800)
    final_audio = synthesize_audio(chunks, output_base=OUTDIR / f"weekly-podcast-of-podcasts-{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')}")
    print(f"Weekly podcast-of-podcasts ready: {final_audio}")
    print(f"MEDIA:{final_audio}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
