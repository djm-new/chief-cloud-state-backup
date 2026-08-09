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
import asyncio
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import requests
import edge_tts

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = Path("/opt/data/podcast_digest")
OUTDIR = BASE / "outputs"
DAILY_GLOB = "*daily-podcast-digest-24h.md"
WEEKLY_MODEL = os.getenv("PODCAST_WEEKLY_MODEL", "qwen/qwen3-235b-a22b")
# Default to edge (cloud, ships with the gateway venv, no disk cost).  The
# local engines need /opt/data/venvs/podcast-tts, which orphaned in June 2026
# and was removed; defaulting to kokoro silently killed the audio step for six
# weeks while the script artifacts kept being written.
WEEKLY_TTS_BACKEND = os.getenv("PODCAST_WEEKLY_TTS_BACKEND", "edge").strip().lower()
WEEKLY_TTS_PYTHON = os.getenv("PODCAST_WEEKLY_TTS_PYTHON", "/opt/data/venvs/podcast-tts/bin/python")
WEEKLY_OUTPUT_SPEED = float(os.getenv("PODCAST_WEEKLY_OUTPUT_SPEED", "1.5") or "1.5")
WEEKLY_PIPER_PYTHON = os.getenv("PODCAST_WEEKLY_PIPER_PYTHON", WEEKLY_TTS_PYTHON)
WEEKLY_PIPER_VOICE_DIR = Path(os.getenv("PODCAST_WEEKLY_PIPER_VOICE_DIR", "/opt/data/piper-voices"))
WEEKLY_MAYA_PIPER_VOICE = os.getenv("PODCAST_WEEKLY_MAYA_PIPER_VOICE", "en_US-hfc_female-medium")
WEEKLY_SAM_PIPER_VOICE = os.getenv("PODCAST_WEEKLY_SAM_PIPER_VOICE", "en_US-hfc_male-medium")
WEEKLY_MAYA_PIPER_LENGTH = os.getenv("PODCAST_WEEKLY_MAYA_PIPER_LENGTH", "0.96")
WEEKLY_SAM_PIPER_LENGTH = os.getenv("PODCAST_WEEKLY_SAM_PIPER_LENGTH", "1.02")
WEEKLY_MAYA_EDGE_VOICE = os.getenv("PODCAST_WEEKLY_MAYA_VOICE", "en-US-JennyNeural")
WEEKLY_SAM_EDGE_VOICE = os.getenv("PODCAST_WEEKLY_SAM_VOICE", "en-US-GuyNeural")
WEEKLY_MAYA_KOKORO_VOICE = os.getenv("PODCAST_WEEKLY_MAYA_KOKORO_VOICE", "af_heart")
WEEKLY_SAM_KOKORO_VOICE = os.getenv("PODCAST_WEEKLY_SAM_KOKORO_VOICE", "am_eric")
WEEKLY_MAYA_KOKORO_SPEED = os.getenv("PODCAST_WEEKLY_MAYA_KOKORO_SPEED", "1.0")
WEEKLY_SAM_KOKORO_SPEED = os.getenv("PODCAST_WEEKLY_SAM_KOKORO_SPEED", "1.0")
WEEKLY_MAYA_RATE = os.getenv("PODCAST_WEEKLY_MAYA_RATE", "+3%")
WEEKLY_SAM_RATE = os.getenv("PODCAST_WEEKLY_SAM_RATE", "-2%")
WEEKLY_MAYA_PITCH = os.getenv("PODCAST_WEEKLY_MAYA_PITCH", "+2Hz")
WEEKLY_SAM_PITCH = os.getenv("PODCAST_WEEKLY_SAM_PITCH", "-1Hz")
WEEKLY_TRANSCRIBE_AUDIO = os.getenv("PODCAST_WEEKLY_TRANSCRIBE_AUDIO", "1").strip().lower() not in {"0", "false", "no"}
WEEKLY_STT_PYTHON = os.getenv("PODCAST_WEEKLY_STT_PYTHON", "/opt/data/venvs/podcast-stt/bin/python")
WEEKLY_STT_MODEL = os.getenv("PODCAST_WEEKLY_STT_MODEL", "base")
WEEKLY_STT_MAX_SECONDS = int(os.getenv("PODCAST_WEEKLY_STT_MAX_SECONDS", "0") or "0")
TRANSCRIPT_DIR = BASE / "transcripts"

sys.path.insert(0, "/opt/data/scripts")
sys.path.insert(0, "/opt/hermes")

from openrouter_spend import openrouter_post_json  # noqa: E402


def clean(text: str, limit: int = 1800) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[:limit]



def speaker_voice(speaker: str) -> dict[str, str]:
    speaker = speaker.upper().strip()
    if speaker == "MAYA":
        return {
            "backend": WEEKLY_TTS_BACKEND,
            "piper_voice": WEEKLY_MAYA_PIPER_VOICE,
            "piper_length": WEEKLY_MAYA_PIPER_LENGTH,
            "kokoro_voice": WEEKLY_MAYA_KOKORO_VOICE,
            "kokoro_speed": WEEKLY_MAYA_KOKORO_SPEED,
            "edge_voice": WEEKLY_MAYA_EDGE_VOICE,
            "edge_rate": WEEKLY_MAYA_RATE,
            "edge_pitch": WEEKLY_MAYA_PITCH,
        }
    if speaker == "SAM":
        return {
            "backend": WEEKLY_TTS_BACKEND,
            "piper_voice": WEEKLY_SAM_PIPER_VOICE,
            "piper_length": WEEKLY_SAM_PIPER_LENGTH,
            "kokoro_voice": WEEKLY_SAM_KOKORO_VOICE,
            "kokoro_speed": WEEKLY_SAM_KOKORO_SPEED,
            "edge_voice": WEEKLY_SAM_EDGE_VOICE,
            "edge_rate": WEEKLY_SAM_RATE,
            "edge_pitch": WEEKLY_SAM_PITCH,
        }
    return {
        "backend": WEEKLY_TTS_BACKEND,
        "piper_voice": WEEKLY_MAYA_PIPER_VOICE,
        "piper_length": WEEKLY_MAYA_PIPER_LENGTH,
        "kokoro_voice": WEEKLY_MAYA_KOKORO_VOICE,
        "kokoro_speed": WEEKLY_MAYA_KOKORO_SPEED,
        "edge_voice": WEEKLY_MAYA_EDGE_VOICE,
        "edge_rate": "+0%",
        "edge_pitch": "+0Hz",
    }


def strip_spoken_markup(text: str) -> str:
    text = re.sub(r"\[(INTRO MUSIC|OUTRO MUSIC|BEAT|PAUSE|LAUGH|SFX|MUSIC)[^\]]*\]", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_dialogue(script: str) -> list[dict[str, Any]]:
    """Parse MAYA:/SAM: dialogue and stage cues into production segments."""
    segments: list[dict[str, Any]] = []
    current_speaker: str | None = None
    current_text: list[str] = []

    def flush() -> None:
        nonlocal current_speaker, current_text
        if current_speaker and current_text:
            text = strip_spoken_markup(" ".join(current_text))
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                segments.append({"type": "speech", "speaker": current_speaker, "text": text})
        current_speaker = None
        current_text = []

    for raw in script.splitlines():
        line = re.sub(r"\*\*", "", raw).strip()
        if not line:
            flush()
            continue
        if line.startswith("## "):
            flush()
            segments.append({"type": "pause", "seconds": 0.5})
            continue
        if re.match(r"^\[(INTRO MUSIC|OUTRO MUSIC|MUSIC|BEAT|PAUSE|SFX)\b", line, flags=re.I):
            flush()
            if "INTRO" in line.upper():
                segments.append({"type": "pause", "seconds": 0.8})
            elif "OUTRO" in line.upper():
                segments.append({"type": "pause", "seconds": 0.9})
            else:
                segments.append({"type": "pause", "seconds": 0.35})
            continue
        m = re.match(r"^(MAYA|SAM):\s*(.*)$", line)
        if m:
            flush()
            current_speaker = m.group(1)
            if m.group(2).strip():
                current_text = [m.group(2)]
            else:
                current_text = []
            continue
        if current_speaker:
            current_text.append(line)
    flush()
    return segments


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


def lookup_episode_row(show: str, episode: str) -> dict[str, str]:
    """Best-effort lookup in the local episode DB for richer episode metadata."""
    con = sqlite3.connect(BASE / "episodes.sqlite")
    try:
        rows = con.execute(
            """
            select show_name, title, link, audio_url, summary
            from episodes
            where lower(show_name) like ? or lower(title) like ?
            order by published desc
            limit 5
            """,
            (f"%{show.lower()}%", f"%{episode.lower()}%"),
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return {}
    best = rows[0]
    return {"show_name": best[0] or "", "title": best[1] or "", "link": best[2] or "", "audio_url": best[3] or "", "summary": best[4] or ""}



def fetch_page_text(url: str, limit: int = 7000) -> dict[str, Any]:
    if not url:
        return {"text": "", "meta_description": "", "transcript_like": False, "status": "missing_url"}
    headers = {"User-Agent": "Mozilla/5.0 Hermes Podcast Digest"}
    try:
        resp = requests.get(url, headers=headers, timeout=25)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        return {"text": "", "meta_description": "", "transcript_like": False, "status": f"fetch_failed:{type(e).__name__}"}
    meta_desc = ""
    m = re.search(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        meta_desc = clean(m.group(1), 1200)
    html = re.sub(r'(?is)<(script|style|noscript|svg).*?>.*?</\1>', ' ', html)
    html = re.sub(r'(?is)<header.*?>.*?</header>', ' ', html)
    html = re.sub(r'(?is)<footer.*?>.*?</footer>', ' ', html)
    html = re.sub(r'(?is)<nav.*?>.*?</nav>', ' ', html)
    html = re.sub(r'(?is)<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', html).strip()
    transcript_like = len(text) > 2500 or re.search(r'(?i)\btranscript\b|speaker|monday|m:|s:', text) is not None
    if not text and meta_desc:
        text = meta_desc
    if text and len(text) < 400 and meta_desc and len(meta_desc) > len(text):
        text = meta_desc
    return {"text": clean(text, limit), "meta_description": meta_desc, "transcript_like": transcript_like, "status": "ok"}


def stable_episode_key(show: str, episode: str, audio_url: str = "") -> str:
    raw = "|".join([show or "", episode or "", audio_url or ""])
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def download_episode_audio(audio_url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1024 * 1024:
        return dest
    headers = {"User-Agent": "Mozilla/5.0 Hermes Podcast Digest"}
    with requests.get(audio_url, headers=headers, stream=True, timeout=(20, 300), allow_redirects=True) as resp:
        resp.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)
    return dest


def transcribe_episode_audio(show: str, episode: str, audio_url: str) -> dict[str, Any]:
    if not WEEKLY_TRANSCRIBE_AUDIO:
        return {"status": "disabled", "text": "", "notes": ""}
    if not audio_url:
        return {"status": "missing_audio_url", "text": "", "notes": ""}
    if not Path(WEEKLY_STT_PYTHON).exists():
        return {"status": f"missing_stt_python:{WEEKLY_STT_PYTHON}", "text": "", "notes": ""}

    key = stable_episode_key(show, episode, audio_url)
    episode_dir = TRANSCRIPT_DIR / key
    episode_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = episode_dir / "transcript.txt"
    notes_path = episode_dir / "chunk-notes.md"
    meta_path = episode_dir / "meta.json"
    if transcript_path.exists() and transcript_path.stat().st_size > 500:
        cache_ok = True
        if meta_path.exists():
            try:
                cache_meta = json.loads(meta_path.read_text(encoding="utf-8"))
                cache_ok = int(cache_meta.get("max_seconds", 0) or 0) == WEEKLY_STT_MAX_SECONDS
            except Exception:
                cache_ok = WEEKLY_STT_MAX_SECONDS == 0
        else:
            cache_ok = WEEKLY_STT_MAX_SECONDS == 0
        if cache_ok:
            text = transcript_path.read_text(encoding="utf-8", errors="ignore")
            notes = notes_path.read_text(encoding="utf-8", errors="ignore") if notes_path.exists() else condense_transcript_to_notes(show, episode, text, notes_path)
            return {"status": "cached", "text": clean(text, 18000), "notes": notes, "path": str(transcript_path), "meta_path": str(meta_path)}
        transcript_path.unlink(missing_ok=True)
        notes_path.unlink(missing_ok=True)

    audio_path = episode_dir / "audio.mp3"
    try:
        download_episode_audio(audio_url, audio_path)
    except Exception as e:
        return {"status": f"download_failed:{type(e).__name__}", "text": "", "notes": ""}

    input_path = audio_path
    if WEEKLY_STT_MAX_SECONDS > 0:
        clip_path = episode_dir / f"audio-first-{WEEKLY_STT_MAX_SECONDS}s.wav"
        cmd = ["ffmpeg", "-y", "-i", str(audio_path), "-t", str(WEEKLY_STT_MAX_SECONDS), "-ac", "1", "-ar", "16000", str(clip_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if res.returncode != 0:
            return {"status": f"clip_failed:{res.stderr[-300:]}", "text": "", "notes": ""}
        input_path = clip_path

    helper = r'''
import json, sys
from faster_whisper import WhisperModel
input_path, model_name, out_path = sys.argv[1:4]
model = WhisperModel(model_name, device="cpu", compute_type="int8")
segments, info = model.transcribe(input_path, language="en", vad_filter=True, beam_size=5)
rows = []
for seg in segments:
    rows.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
text = "\n".join(f"[{r['start']:.1f}-{r['end']:.1f}] {r['text']}" for r in rows if r["text"])
open(out_path, "w", encoding="utf-8").write(text + "\n")
print(json.dumps({"language": getattr(info, "language", None), "duration": getattr(info, "duration", None), "segments": len(rows)}))
'''
    cmd = [WEEKLY_STT_PYTHON, "-c", helper, str(input_path), WEEKLY_STT_MODEL, str(transcript_path)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=7200, env={**os.environ, "HF_HOME": "/opt/data/huggingface"})
    except subprocess.TimeoutExpired:
        return {"status": "transcribe_timeout", "text": "", "notes": ""}
    if res.returncode != 0:
        return {"status": f"transcribe_failed:{res.stderr[-700:]}", "text": "", "notes": ""}
    text = transcript_path.read_text(encoding="utf-8", errors="ignore") if transcript_path.exists() else ""
    meta = {"show": show, "episode": episode, "audio_url": audio_url, "model": WEEKLY_STT_MODEL, "max_seconds": WEEKLY_STT_MAX_SECONDS, "stdout": res.stdout.strip()}
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    notes = condense_transcript_to_notes(show, episode, text, notes_path)
    return {"status": "transcribed", "text": clean(text, 18000), "notes": notes, "path": str(transcript_path), "meta_path": str(meta_path)}


def transcript_chunks(text: str, max_chars: int = 12000) -> list[str]:
    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n{para}".strip() if current else para
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = para
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def condense_transcript_to_notes(show: str, episode: str, transcript: str, notes_path: Path) -> str:
    if notes_path.exists() and notes_path.stat().st_size > 200:
        return notes_path.read_text(encoding="utf-8", errors="ignore")
    chunks = transcript_chunks(transcript)[:12]
    if not chunks:
        return ""
    all_notes = []
    for idx, chunk in enumerate(chunks, 1):
        prompt = (
            "/no_think\n"
            f"You are extracting evidence for DJ's weekly podcast digest. Episode: {show} — {episode}.\n"
            "From this transcript chunk, extract only concrete arguments, claims, evidence, frameworks, counterpoints, and DJ-relevant takeaways. "
            "Do not write a polished summary. Use compact bullets with speaker-specific details when available.\n\n"
            f"Transcript chunk {idx}/{len(chunks)}:\n{chunk}"
        )
        resp = openrouter_post_json(
            path="chat/completions",
            model=WEEKLY_MODEL,
            title="Hermes Podcast Transcript Chunk Extraction",
            referer="https://hermes-agent.local/podcast-digest",
            timeout=180,
            payload={
                "model": WEEKLY_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.15,
                "max_tokens": 900,
            },
            source="cron",
            platform="cron",
            project_slug="podcast-intelligence-digest",
            workdir=str(BASE),
            metadata={"workflow": "podcast-intelligence-digest", "stage": "weekly_transcript_chunk_extract", "chunk": idx, "chunks": len(chunks)},
        )
        all_notes.append(f"### Chunk {idx}\n" + resp["choices"][0]["message"]["content"].strip())
    notes = "\n\n".join(all_notes)
    notes_path.write_text(notes + "\n", encoding="utf-8")
    return notes


def build_source_briefs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    briefs = []
    for item in items:
        lookup = lookup_episode_row(item["show"], item["episode"])
        page_url = lookup.get("link") or item.get("link", "")
        audio_url = lookup.get("audio_url", "")
        page = fetch_page_text(page_url)
        audio_grounding = {"status": "not_needed", "text": "", "notes": ""}
        if not page.get("transcript_like", False) and audio_url:
            audio_grounding = transcribe_episode_audio(item["show"], item["episode"], audio_url)
        briefs.append(
            {
                "show": item["show"],
                "episode": item["episode"],
                "link": page_url,
                "audio_url": audio_url,
                "section": item.get("section", ""),
                "what": item.get("what", ""),
                "why": item.get("why", ""),
                "page_text": page.get("text", ""),
                "page_meta_description": page.get("meta_description", ""),
                "page_transcript_like": page.get("transcript_like", False),
                "page_status": page.get("status", ""),
                "audio_transcript_status": audio_grounding.get("status", ""),
                "audio_transcript_path": audio_grounding.get("path", ""),
                "audio_transcript_notes": audio_grounding.get("notes", ""),
                "audio_transcript_excerpt": audio_grounding.get("text", ""),
                "source_file": item.get("date_file", ""),
            }
        )
    return briefs


def draft_weekly_script(source_briefs: list[dict[str, Any]], window_days: int) -> tuple[str, dict[str, Any]]:
    system = """You write DJ Mauch's weekly podcast digest as an episode-first two-host show.
The previous failure mode was turning the week into a generic theme essay. Do not do that.
A successful digest MUST name the show, guest, episode/conversation, thesis, and DJ-relevant takeaway for each selected podcast before doing synthesis.
Use the supplied briefs as source material only; do not invent specific facts.
Tailor the relevance to DJ's taste: CEOs, top investors, AI leaders, platform strategy, software economics, capital allocation, durable frameworks.
The show should sound conversational, but the structure is a digest: each segment is anchored to one podcast episode.
Host dynamic: MAYA is the expert/reviewer who listened/read deeply; SAM is the interlocutor who asks clarifying questions, challenges the expert, draws out implications, and adds background/context.
Speaker labels are directions only; never speak the labels.
Avoid abstract openings, vague themes, formulaic turn-taking, and generic "AI is changing everything" phrasing."""
    user = (
        "/no_think\n"
        f"Create a 15-20 minute weekly podcast digest script for the last {window_days} days. "
        "Use speaker labels exactly as MAYA: and SAM:. MAYA is the expert/reviewer; SAM is the interlocutor. "
        "SAM should ask natural clarifying questions, draw out implications, add context/background, and challenge weak points. "
        "MAYA should answer from the source material and explain why the episode matters. "
        "Open with a concrete intro in this form: 'This week, we'll hear from [guest] on [specific thesis]; from [guest] on [specific thesis]; and from [guest] on [specific thesis].' "
        "Then proceed episode by episode and cover EVERY supplied source brief; do not silently drop any finalist. "
        "For EACH episode segment, start by naming the show, episode title, and guest if known. "
        "For each episode, spend multiple turns explaining: main thesis, strongest argument/evidence, counterpoint or open question, and why DJ should care. "
        "Make this value-added: explain the reasoning and tradeoffs from the transcript notes, not just a one-paragraph recap. "
        "Only synthesize across episodes after the episode-level sections are clear. "
        "Each speaker turn should be 1-3 sentences and sound natural when spoken. "
        "Do not include bullets in the spoken script. Do not flatten episodes into topical segments. "
        "Use audio_transcript_notes/audio_transcript_excerpt or page_text/transcript-like excerpts as primary grounding when present; only fall back to metadata when neither transcript nor audio transcript exists. "
        "If a source says audio_transcript_status=transcribed or cached, treat that as the podcast having been listened to via STT. "
        "Use only details present in the briefs. Source briefs:\n"
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
            "max_tokens": 9000,
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


def sanitize_speech_text(text: str) -> str:
    text = text.replace("**", "")
    text = re.sub(r"\[(INTRO MUSIC|OUTRO MUSIC|BEAT|PAUSE|SFX|MUSIC)[^\]]*\]", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_if_needed(text: str, limit: int = 3200) -> list[str]:
    text = sanitize_speech_text(text)
    if len(text) <= limit:
        return [text]
    parts = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current} {part}".strip() if current else part
        if current and len(candidate) > limit:
            out.append(current)
            current = part
        else:
            current = candidate
    if current:
        out.append(current)
    return [p for p in out if p.strip()]


async def synthesize_edge_mp3(text: str, voice: str, rate: str, pitch: str, output_path: Path) -> Path:
    comm = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await comm.save(str(output_path))
    if not output_path.exists() or output_path.stat().st_size <= 0:
        raise RuntimeError(f"Edge TTS did not produce {output_path}")
    return output_path


def ensure_piper_voice(model_name: str) -> Path:
    WEEKLY_PIPER_VOICE_DIR.mkdir(parents=True, exist_ok=True)
    model_path = WEEKLY_PIPER_VOICE_DIR / f"{model_name}.onnx"
    config_path = WEEKLY_PIPER_VOICE_DIR / f"{model_name}.onnx.json"
    if model_path.exists() and config_path.exists():
        return model_path
    cmd = [WEEKLY_PIPER_PYTHON, "-m", "piper.download_voices", model_name, "--download-dir", str(WEEKLY_PIPER_VOICE_DIR)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Piper voice download failed for {model_name}: {res.stderr[-500:]}")
    if not model_path.exists() or not config_path.exists():
        raise RuntimeError(f"Piper voice files missing after download for {model_name}")
    return model_path


def synthesize_piper_wav(text: str, model_name: str, speed: str, output_path: Path) -> Path:
    model_path = ensure_piper_voice(model_name)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as tmp:
        tmp.write(text)
        input_path = Path(tmp.name)
    try:
        cmd = [
            WEEKLY_PIPER_PYTHON,
            "-m",
            "piper",
            "-m",
            str(model_path),
            "-f",
            str(output_path),
            "-i",
            str(input_path),
            "--length-scale",
            str(speed),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Piper TTS failed: {res.stderr[-500:]}")
        if not output_path.exists() or output_path.stat().st_size <= 0:
            raise RuntimeError(f"Piper TTS did not produce {output_path}")
        return output_path
    finally:
        try:
            input_path.unlink(missing_ok=True)
        except Exception:
            pass


def synthesize_kokoro_wav(text: str, voice: str, speed: str, output_path: Path) -> Path:
    helper = r'''
import sys
from pathlib import Path
from kokoro import KPipeline
import soundfile as sf
text_path, voice, speed, output_path = sys.argv[1:5]
text = Path(text_path).read_text(encoding="utf-8")
p = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
parts = []
for result in p(text, voice=voice, speed=float(speed)):
    sf.write(output_path, result.audio, 24000)
    break
'''
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as tmp:
        tmp.write(text)
        input_path = Path(tmp.name)
    try:
        cmd = [WEEKLY_TTS_PYTHON, "-c", helper, str(input_path), voice, str(speed), str(output_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Kokoro TTS failed: {res.stderr[-800:]}")
        if not output_path.exists() or output_path.stat().st_size <= 0:
            raise RuntimeError(f"Kokoro TTS did not produce {output_path}")
        return output_path
    finally:
        input_path.unlink(missing_ok=True)


def ffmpeg_to_wav(input_path: Path, output_path: Path) -> Path:
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(output_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg wav conversion failed: {res.stderr[-500:]}")
    return output_path


def make_silence_wav(output_path: Path, seconds: float) -> Path:
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
        "-t", f"{seconds:.3f}", "-c:a", "pcm_s16le", str(output_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg silence generation failed: {res.stderr[-500:]}")
    return output_path


def resolve_tts_backend() -> str:
    """Return a backend that can actually run right now.

    piper and kokoro both shell out to WEEKLY_TTS_PYTHON.  If that interpreter
    is gone (deleted venv, wiped volume, orphaned pyvenv.cfg), fall back to
    edge rather than dying after the script artifacts have already been
    written — that failure mode looked like "runs clean, produces nothing".
    """
    backend = WEEKLY_TTS_BACKEND
    if backend not in {"piper", "kokoro"}:
        return backend
    interpreter = WEEKLY_PIPER_PYTHON if backend == "piper" else WEEKLY_TTS_PYTHON
    if Path(interpreter).exists():
        return backend
    print(
        f"WARNING: TTS backend '{backend}' needs {interpreter}, which is missing. "
        f"Falling back to edge.",
        file=sys.stderr,
    )
    return "edge"


def synthesize_audio(script: str, output_base: Path) -> Path:
    segments = parse_dialogue(script)
    if not segments:
        raise RuntimeError("No dialogue segments found to synthesize")

    backend = resolve_tts_backend()

    audio_paths: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="weekly-podcast-tts-") as tmpdir:
        tmp = Path(tmpdir)
        seg_idx = 0
        for seg in segments:
            seg_idx += 1
            if seg["type"] == "pause":
                silence = make_silence_wav(tmp / f"pause-{seg_idx}.wav", float(seg.get("seconds", 0.25)))
                audio_paths.append(silence)
                continue

            speaker = str(seg.get("speaker", "MAYA"))
            voice_cfg = speaker_voice(speaker)
            parts = split_if_needed(str(seg.get("text", "")))
            for part_idx, part in enumerate(parts, 1):
                if backend == "piper":
                    wav_path = tmp / f"{seg_idx}-{speaker.lower()}-{part_idx}.wav"
                    audio_paths.append(
                        synthesize_piper_wav(
                            part,
                            model_name=voice_cfg["piper_voice"],
                            speed=voice_cfg["piper_length"],
                            output_path=wav_path,
                        )
                    )
                elif backend == "kokoro":
                    wav_path = tmp / f"{seg_idx}-{speaker.lower()}-{part_idx}.wav"
                    audio_paths.append(
                        synthesize_kokoro_wav(
                            part,
                            voice=voice_cfg["kokoro_voice"],
                            speed=voice_cfg["kokoro_speed"],
                            output_path=wav_path,
                        )
                    )
                else:
                    mp3_path = tmp / f"{seg_idx}-{speaker.lower()}-{part_idx}.mp3"
                    wav_path = tmp / f"{seg_idx}-{speaker.lower()}-{part_idx}.wav"
                    asyncio.run(
                        synthesize_edge_mp3(
                            part,
                            voice=voice_cfg["edge_voice"],
                            rate=voice_cfg["edge_rate"],
                            pitch=voice_cfg["edge_pitch"],
                            output_path=mp3_path,
                        )
                    )
                    audio_paths.append(ffmpeg_to_wav(mp3_path, wav_path))
                if part_idx != len(parts):
                    audio_paths.append(make_silence_wav(tmp / f"gap-{seg_idx}-{part_idx}.wav", 0.16))

        list_path = tmp / "concat.txt"
        list_path.write_text("".join(f"file '{p}'\n" for p in audio_paths), encoding="utf-8")
        final_ogg = output_base.with_suffix(".ogg")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
            "-ac", "1", "-b:a", "64k", "-vbr", "off",
        ]
        if abs(WEEKLY_OUTPUT_SPEED - 1.0) > 0.001:
            cmd.extend(["-filter:a", f"atempo={WEEKLY_OUTPUT_SPEED:g}"])
        cmd.extend(["-acodec", "libopus", str(final_ogg)])
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
        tz_ok = True
        try:
            from zoneinfo import ZoneInfo
            et_hour = dt.datetime.now(ZoneInfo("America/New_York")).hour
        except Exception as tz_err:
            # Without tzdata this falls back to UTC, which never equals 17 —
            # the job would no-op forever.  Say so instead of exiting silently.
            tz_ok = False
            et_hour = dt.datetime.now(dt.timezone.utc).hour
            print(f"WARNING: ZoneInfo unavailable ({tz_err}); using UTC hour "
                  f"{et_hour}. The 17:00-ET gate cannot match — set "
                  f"PODCAST_WEEKLY_FORCE_RUN=1 or install tzdata.",
                  file=sys.stderr)
        if et_hour != 17:
            # Cron fires at both 21:00 and 22:00 UTC so one of them lands on
            # 17:00 ET in either DST state; the other is expected to no-op.
            print(f"Skipping: hour is {et_hour} ({'ET' if tz_ok else 'UTC'}), "
                  f"job only runs at 17:00 ET. "
                  f"Use PODCAST_WEEKLY_FORCE_RUN=1 to override.")
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
    transcript_like_count = sum(1 for b in source_briefs if b.get("page_transcript_like"))
    audio_transcribed_count = sum(1 for b in source_briefs if b.get("audio_transcript_status") in {"transcribed", "cached"})
    script, usage = draft_weekly_script(source_briefs, window_days=args.days)
    artifacts = save_artifacts(
        base_name="weekly-podcast-of-podcasts",
        script=script,
        tts_text=script,
        source_briefs=source_briefs,
        usage=usage,
        model=WEEKLY_MODEL,
    )
    print(f"Wrote script: {artifacts['script']}")
    print(f"Wrote sources: {artifacts['sources']}")
    print(f"Wrote meta: {artifacts['meta']}")
    print(f"Transcript-grounded finalists: {transcript_like_count}/{len(source_briefs)}")
    print(f"Audio-transcribed finalists: {audio_transcribed_count}/{len(source_briefs)}")
    print(f"Weekly script model usage: {usage}")

    if args.dry_run:
        print(script)
        return 0

    tts_text = artifacts["tts"].read_text(encoding="utf-8")
    final_audio = synthesize_audio(tts_text, output_base=OUTDIR / f"weekly-podcast-of-podcasts-{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')}")
    print(f"Weekly podcast-of-podcasts ready: {final_audio}")
    print(f"MEDIA:{final_audio}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
