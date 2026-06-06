#!/usr/bin/env python3
"""Hermes Thought Capture & Synthesis System.

Local-first markdown thought journal with Telegram gateway integration hooks and
cron-callable operations.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DEFAULT_REPO = Path(os.environ.get("THOUGHTS_REPO", "/opt/data/thoughts-repo"))
HERMES = Path(os.environ.get("HERMES_BIN", "/opt/hermes/.venv/bin/hermes"))

VOCAB_SEED = [
    "Pura Vida", "ICONIQ", "Starlight 13", "Riyadh Air", "MFC", "Flow MENA",
    "Hermes", "Chief", "Sandra", "JAWS Ventures", "BMAD",
]

WEEKLY_PROMPT = '''You are synthesizing my thoughts from the past week. You have 7 daily files of raw, timestamped captures. Entries prefixed with `!` are ones I flagged as significant — give them extra weight without treating non-flagged entries as throwaway.

This is not a summary. This is not meeting minutes. Produce:

1. **Themes I returned to repeatedly** (3–5). What did I keep coming back to, in different forms or contexts? Quote briefly to ground each theme. Anchor on intensity-flagged entries where present.

2. **Open questions I'm chewing on.** Things I posed but didn't resolve. What am I still working out?

3. **What shifted.** Any view that changed across the week — even slightly. Quote the before and after if you can. If nothing actually shifted, say so. Do not manufacture shifts.

4. **State of mind.** Pick 2–3 dominant states (building, deciding, processing, anxious, curious, restless, etc.) ONLY if you can ground each with at least 2 specific quoted entries. If you cannot ground it with quotes, skip this section entirely. Do not produce pop psychology.

5. **Threads worth pulling.** Half-formed thoughts that felt interesting but didn't go anywhere. Surface them so I can decide whether to keep developing.

Avoid:
- Enumerating all thoughts
- Summarizing chronologically
- Meeting-minutes style
- Listing every workstream I touched
- Comprehensiveness for its own sake
- Inventing patterns to fill required sections

Be selective. If the week was light, the synthesis should be light. Length matches signal, not effort.
'''

MONTHLY_PROMPT = '''You are synthesizing my thoughts from the past month. Your PRIMARY source is the ~30 daily files. The 4–5 weekly syntheses are provided as a cross-check only — do not roll them up.

This is a state-of-mind snapshot at the monthly level. Produce:

1. **Decisions reached.** Things I was deliberating that actually landed this month. What did I decide and what was the reasoning trail? Quote dailies, not weeklies.

2. **Patterns across weeks.** Themes that recurred or evolved through the month. What's compounding? What's fading? Cite specific daily entries.

3. **View changes.** Explicit shifts in how I see something — investment thesis, operational call, strategic frame, view of a person or company. Quote the before and after from dailies.

4. **Convergence vs divergence.** What's clarifying (sharper, more decided) vs getting more complex (more variables, less certain)?

5. **Workstream cross-section.** One short paragraph each on what's top of mind across: Flow (incl. MENA), 166 2nd, M Family Co, Chief/Hermes, personal. Skip any workstream that was genuinely quiet — do not manufacture coverage.

6. **Predictions to track.** Any implied forecast or expectation I made this month. Be precise: what did I predict, when, with what implied confidence? The quarterly will revisit these.

Cross-check step: after drafting, scan the weeklies. If your monthly contradicts a weekly synthesis without my having written a corresponding view shift in the dailies, flag the discrepancy at the end as a note.

Avoid:
- Rolling up the weeklies
- Treating quiet topics as if they need coverage
- Ego-friendly framing — be honest about what's stalled or confused
'''

QUARTERLY_PROMPT = '''You are synthesizing my thoughts from the past quarter. Your PRIMARY source is the daily corpus (~90 files). The 3 monthly syntheses are cross-check only.

This is the highest-leverage artifact in the system. This is where worldview shifts get named. Produce:

1. **Worldview shifts.** How did my fundamental view of something change this quarter? Be specific — not "I think more about X now" but "I used to believe A, now I believe B, the shift happened around [evidence/date]." Quote dailies.

2. **Where I was wrong.** Revisit predictions/expectations from the prior quarterly (if exists) and from this quarter's monthly "predictions to track" sections. What landed differently than I thought? Be direct about errors. Do not soft-pedal.

3. **Recurring tensions.** Trade-offs that kept showing up across workstreams. Build vs buy, US vs MENA, liquid vs operating, founder-led vs delegated, speed vs durability. What tensions am I living in?

4. **Strategic insights worth acting on.** 3–5 insights that warrant an actual decision or change in approach. Not observations — actionable shifts. For each, state what the action would be.

5. **Patterns I might not see — including negative space.** Two parts:
   (a) What's recurring across my thoughts that I haven't explicitly named myself? What would a sharp outside observer notice from reading this quarter's corpus that I haven't articulated?
   (b) **What topics would you expect from someone in my role and life context that are conspicuously absent?** A senior executive managing Flow + 166 2nd + M Family Co + a family in NYC with three young children — what would you expect to surface that didn't? Negative space is often where the real blind spots live.

6. **Questions for next quarter.** What should I be paying attention to that I might otherwise miss? What are the right questions to be asking myself in the next 90 days?

Avoid:
- Year-in-review framing or ego-stroking
- Listing accomplishments
- Soft-pedaling errors or confusion
- Treating this as a comprehensive summary
- Synthesizing the monthlies instead of the dailies

Be honest. This artifact is for me, not for an audience.
'''

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self.meta_desc = ""
        self.chunks: list[str] = []
    def handle_starttag(self, tag, attrs):
        if tag == "title": self._in_title = True
        if tag == "meta":
            d = dict(attrs)
            if d.get("name", "").lower() == "description" and d.get("content"):
                self.meta_desc = d["content"]
    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False
    def handle_data(self, data):
        s = " ".join(data.split())
        if not s: return
        if self._in_title: self.title += s + " "
        if len(s) > 40: self.chunks.append(s)

@dataclass
class Entry:
    date: str
    time: str
    marker: str
    text: str
    path: Path


def repo() -> Path:
    return DEFAULT_REPO


def run(cmd: list[str], cwd: Path | None = None, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=check)


def git_commit(message: str) -> None:
    r = repo()
    if not (r / ".git").exists():
        run(["git", "init"], cwd=r)
        run(["git", "config", "user.email", "hermes@local"], cwd=r)
        run(["git", "config", "user.name", "Hermes Thought Capture"], cwd=r)
    run(["git", "add", "."], cwd=r)
    diff = run(["git", "diff", "--cached", "--quiet"], cwd=r)
    if diff.returncode == 0:
        return
    run(["git", "commit", "-m", message], cwd=r)


def init_repo() -> None:
    r = repo()
    for p in ["daily", "weekly", "monthly", "quarterly", "attachments", "prompts", "config"]:
        (r / p).mkdir(parents=True, exist_ok=True)
    readme = r / "README.md"
    if not readme.exists():
        readme.write_text(textwrap.dedent(f"""
        # Thoughts Repo

        Local-first Hermes thought capture and synthesis corpus.

        ## Privacy decision

        This repository is local-first. If it is ever pushed to a remote, the remote must be a private GitHub repository only. Sensitive directories (`daily/`, `weekly/`, `monthly/`, `quarterly/`, `attachments/`) must be encrypted at rest with `git-crypt` before any remote push. No cloud backups outside the encrypted private remote are allowed.

        This decision was documented before the first commit, per the build spec.

        ## Capture rules

        - Daily files are append-only.
        - Corrections are new follow-up entries starting with `correction:`; historical entries are never edited.
        - A leading `!` is an intensity flag, not a tag/category.
        - Synthesis prompts are versioned under `prompts/`; editing a prompt requires a commit.
        - Timezone: America/New_York.
        """).strip()+"\n", encoding="utf-8")
    prompts = {"weekly.md": WEEKLY_PROMPT, "monthly.md": MONTHLY_PROMPT, "quarterly.md": QUARTERLY_PROMPT}
    for name, content in prompts.items():
        p = r / "prompts" / name
        if not p.exists(): p.write_text(content.strip()+"\n", encoding="utf-8")
    vocab = r / "config" / "vocab.txt"
    if not vocab.exists(): vocab.write_text("\n".join(VOCAB_SEED)+"\n", encoding="utf-8")
    corr = r / "config" / "corrections.json"
    if not corr.exists(): corr.write_text(json.dumps({"Pure Vida": "Pura Vida"}, indent=2)+"\n", encoding="utf-8")
    (r / ".gitignore").write_text(".DS_Store\n*.tmp\n", encoding="utf-8")
    if not (r / ".git").exists():
        run(["git", "init"], cwd=r)
        run(["git", "config", "user.email", "hermes@local"], cwd=r)
        run(["git", "config", "user.name", "Hermes Thought Capture"], cwd=r)
    git_commit("init: thoughts capture repo")


def day_path(d: date) -> Path:
    return repo() / "daily" / f"{d:%Y}" / f"{d:%m}" / f"{d:%Y-%m-%d}.md"


def ensure_day_file(d: date) -> Path:
    p = day_path(d); p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(f"# {d:%Y-%m-%d} ({d:%A})\n\n", encoding="utf-8")
    return p


def attachment_dir(dt: datetime) -> Path:
    p = repo() / "attachments" / f"{dt:%Y}" / f"{dt:%m}" / f"{dt:%d}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def apply_corrections(text: str) -> str:
    corr_path = repo() / "config" / "corrections.json"
    try: corrections = json.loads(corr_path.read_text(encoding="utf-8"))
    except Exception: corrections = {}
    for pat, repl in corrections.items():
        text = re.sub(pat, repl, text)
    return text


def vocab_prompt() -> str:
    p = repo() / "config" / "vocab.txt"
    return ", ".join([x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]) if p.exists() else ""


def transcribe_voice(path: str) -> str:
    try:
        from faster_whisper import WhisperModel
        model = os.environ.get("THOUGHTS_WHISPER_MODEL", "base")
        m = WhisperModel(model, device="cpu", compute_type="int8")
        segments, _info = m.transcribe(path, beam_size=5, initial_prompt=vocab_prompt() or None)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return apply_corrections(text)
    except Exception:
        try:
            sys.path.insert(0, "/opt/hermes")
            from tools.transcription_tools import transcribe_audio
            res = transcribe_audio(path)
            return apply_corrections(res.get("transcript") or f"[transcription failed: {res.get('error','unknown')}]" )
        except Exception as e:
            return f"[transcription failed: {e}]"


def ocr_image(path: str) -> str:
    # Prefer tesseract if available; otherwise preserve original and record an OCR placeholder.
    if shutil.which("tesseract"):
        out = run(["tesseract", path, "stdout"])
        if out.returncode == 0 and out.stdout.strip(): return out.stdout.strip()
    return "[OCR unavailable locally; image preserved in attachments]"


def summarize_url(url: str) -> str:
    try:
        req = Request(url, headers={"User-Agent":"HermesThoughtCapture/1.0"})
        with urlopen(req, timeout=12) as resp:
            raw = resp.read(250000).decode("utf-8", errors="ignore")
        ex = TextExtractor(); ex.feed(raw)
        title = ex.title.strip()
        desc = ex.meta_desc.strip()
        body = " ".join(ex.chunks[:5])[:600]
        bits = [b for b in [title, desc, body] if b]
        return " ".join(bits)[:900] or "[Fetched URL but could not extract readable text.]"
    except Exception as e:
        return f"[URL fetch failed: {e}]"

URL_RE = re.compile(r"https?://\S+")


def append_entry(text: str, kind: str = "text", media_paths: list[str] | None = None, source: str = "") -> str:
    init_repo()
    now = datetime.now(ET)
    p = ensure_day_file(now.date())
    media_paths = media_paths or []
    marker = ""
    body = text.strip()
    if kind == "voice":
        saved = []
        for mp in media_paths:
            src = Path(mp)
            dest = attachment_dir(now) / f"{now:%H%M%S}{src.suffix or '.ogg'}"
            shutil.copy2(src, dest); saved.append(str(dest))
        body = transcribe_voice(saved[0] if saved else media_paths[0]) if (saved or media_paths) else "[voice received but no audio path]"
        marker = " [voice]"
    elif kind == "image":
        saved = []
        for i, mp in enumerate(media_paths):
            src = Path(mp); dest = attachment_dir(now) / f"{now:%H%M%S}_{i}{src.suffix or '.jpg'}"
            shutil.copy2(src, dest); saved.append(str(dest))
        body = "\n\n".join(ocr_image(x) for x in saved) if saved else "[image received but no image path]"
        marker = " [image]"
    elif kind == "link":
        urls = URL_RE.findall(body)
        if urls:
            marker = f" [link] {urls[0]}"
            body = summarize_url(urls[0])
    elif kind == "forwarded":
        marker = " [forwarded]"
        if source: body = f"Source: {source}\n\n{body}"
    else:
        urls = URL_RE.findall(body)
        if urls and body.strip() == urls[0]:
            marker = f" [link] {urls[0]}"; body = summarize_url(urls[0])
    # Intensity convention: leading ! gets marker, not category/tag.
    if text.strip().startswith("!") and "!" not in marker:
        marker += " !"
    with p.open("a", encoding="utf-8") as f:
        f.write(f"## {now:%H:%M}{marker}\n{body}\n\n")
    git_commit(f"capture: {now:%Y-%m-%d %H:%M}")
    return str(p)


def parse_entries(paths: Iterable[Path]) -> list[Entry]:
    entries: list[Entry] = []
    for p in paths:
        if not p.exists(): continue
        current_time = ""; marker = ""; buf=[]
        d = p.stem
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^##\s+(\d\d:\d\d)(.*)$", line)
            if m:
                if current_time:
                    entries.append(Entry(d, current_time, marker.strip(), "\n".join(buf).strip(), p))
                current_time, marker, buf = m.group(1), m.group(2), []
            elif current_time:
                buf.append(line)
        if current_time:
            entries.append(Entry(d, current_time, marker.strip(), "\n".join(buf).strip(), p))
    return entries


def close_daily(target: date | None = None) -> str:
    init_repo(); d = target or (datetime.now(ET).date() - timedelta(days=1))
    p = ensure_day_file(d)
    txt = p.read_text(encoding="utf-8")
    if "\n---\n\nFooter:" in txt: return str(p)
    entries = parse_entries([p])
    voice = sum("[voice]" in e.marker for e in entries)
    link = sum("[link]" in e.marker for e in entries)
    intensity = sum("!" in e.marker for e in entries)
    words = sum(len(re.findall(r"\w+", e.text)) for e in entries)
    footer = f"---\n\nFooter: total entries: {len(entries)}; voice count: {voice}; link count: {link}; intensity-flagged count: {intensity}; total estimated word count: {words}.\n"
    p.write_text(txt.rstrip()+"\n\n"+footer, encoding="utf-8")
    git_commit(f"daily: {d:%Y-%m-%d} ({len(entries)} entries)")
    return str(p)


def read_daily(target: date | None = None) -> str:
    d = target or (datetime.now(ET).date() - timedelta(days=1))
    p = day_path(d)
    return p.read_text(encoding="utf-8") if p.exists() else f"No daily file for {d:%Y-%m-%d}."


def prompt_llm(prompt: str, timeout: int = 300) -> str:
    if HERMES.exists():
        cp = run([str(HERMES), "chat", "-q", prompt, "--provider", "openai", "--model", "gpt-5.2"], cwd=repo())
        if cp.returncode == 0 and cp.stdout.strip(): return cp.stdout.strip()
    return fallback_synthesis(prompt)


def fallback_synthesis(context: str) -> str:
    # Extractive fallback that preserves quotes when LLM is unavailable.
    lines = [l.strip() for l in context.splitlines() if l.strip()]
    flagged = [l for l in lines if "## " in l and "!" in l]
    quotes = [l for l in lines if not l.startswith("#") and len(l) > 30][:12]
    return "# Fallback synthesis\n\nLLM synthesis unavailable; showing high-signal excerpts.\n\n" + "\n".join(f"- {q[:240]}" for q in (flagged + quotes)[:16]) + "\n"


def first_saturday_at_least_5_days_after(d: date) -> date:
    candidate = d + timedelta(days=5)
    while candidate.weekday() != 5:  # Saturday
        candidate += timedelta(days=1)
    return candidate


def create_quarterly_review_calendar_block(run_date: date, synthesis: str) -> None:
    """Create the quarterly review calendar block when Google local account is available.

    Uses DJ's local Google account wrapper and creates no attendees, respecting the
    local no-notifications policy.
    """
    wrapper = Path("/opt/data/scripts/google-account")
    if not wrapper.exists():
        return
    q = (run_date.month - 1) // 3 + 1
    review_day = first_saturday_at_least_5_days_after(run_date.replace(day=1))
    start = datetime(review_day.year, review_day.month, review_day.day, 9, 0, tzinfo=ET)
    end = start + timedelta(minutes=90)
    desc = synthesis[:7000]
    run([
        str(wrapper), "personal", "calendar", "create",
        "--summary", f"Review Q{q} synthesis",
        "--start", start.isoformat(),
        "--end", end.isoformat(),
        "--description", desc,
    ])


def iso_week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def synthesize(kind: str, today: date | None = None) -> str:
    init_repo(); today = today or datetime.now(ET).date()
    if kind == "weekly":
        start = iso_week_monday(today) - timedelta(days=7); end = start + timedelta(days=6)
        daily_paths = [day_path(start + timedelta(days=i)) for i in range(7)]
        prompt = (repo()/"prompts"/"weekly.md").read_text(encoding="utf-8")
        iso = start.isocalendar(); out = repo()/"weekly"/f"{iso.year}"/f"{iso.year}-W{iso.week:02d}.md"
        title = f"# {iso.year}-W{iso.week:02d} ({start:%Y-%m-%d} to {end:%Y-%m-%d})\n\n"
        context = "\n\n".join(p.read_text(encoding="utf-8") for p in daily_paths if p.exists())
    elif kind == "monthly":
        first_this = today.replace(day=1); end = first_this - timedelta(days=1); start = end.replace(day=1)
        daily_paths=[]; d=start
        while d<=end: daily_paths.append(day_path(d)); d+=timedelta(days=1)
        prompt = (repo()/"prompts"/"monthly.md").read_text(encoding="utf-8")
        out = repo()/"monthly"/f"{start:%Y}"/f"{start:%Y-%m}.md"; title=f"# {start:%Y-%m}\n\n"
        weeklies = sorted((repo()/"weekly").glob(f"{start:%Y}/**/*.md"))
        context = "PRIMARY DAILY FILES:\n\n" + "\n\n".join(p.read_text(encoding="utf-8") for p in daily_paths if p.exists()) + "\n\nWEEKLIES CROSS-CHECK ONLY:\n\n" + "\n\n".join(p.read_text(encoding="utf-8") for p in weeklies)
    elif kind == "quarterly":
        q = (today.month-1)//3 + 1; start_month = 3*(q-2)+1
        year = today.year
        if start_month <= 0: start_month += 12; year -= 1
        start = date(year, start_month, 1)
        next_q_month = start_month + 3; next_year = year
        if next_q_month > 12: next_q_month -= 12; next_year += 1
        end = date(next_year, next_q_month, 1) - timedelta(days=1)
        daily_paths=[]; d=start
        while d<=end: daily_paths.append(day_path(d)); d+=timedelta(days=1)
        prompt = (repo()/"prompts"/"quarterly.md").read_text(encoding="utf-8")
        qn=(start.month-1)//3+1; out=repo()/"quarterly"/f"{start:%Y}"/f"{start:%Y}-Q{qn}.md"; title=f"# {start:%Y}-Q{qn}\n\n"
        monthlies = sorted((repo()/"monthly"/f"{start:%Y}").glob("*.md")) if (repo()/"monthly"/f"{start:%Y}").exists() else []
        context = "PRIMARY DAILY FILES:\n\n" + "\n\n".join(p.read_text(encoding="utf-8") for p in daily_paths if p.exists()) + "\n\nMONTHLIES CROSS-CHECK ONLY:\n\n" + "\n\n".join(p.read_text(encoding="utf-8") for p in monthlies)
    else:
        raise SystemExit("kind must be weekly/monthly/quarterly")
    out.parent.mkdir(parents=True, exist_ok=True)
    body = prompt_llm(prompt + "\n\n--- SOURCE MATERIAL ---\n\n" + context[:120000])
    out.write_text(title + body.strip() + "\n", encoding="utf-8")
    git_commit(f"{kind}: {out.stem}")
    if kind == "weekly": suggest_vocab(start, end)
    if kind == "quarterly" and os.environ.get("THOUGHTS_ENABLE_CALENDAR", "0") == "1":
        try:
            create_quarterly_review_calendar_block(today, out.read_text(encoding="utf-8"))
        except Exception:
            pass
    return str(out)


def suggest_vocab(start: date, end: date) -> None:
    vocab = set(x.strip() for x in (repo()/"config"/"vocab.txt").read_text(encoding="utf-8").splitlines() if x.strip())
    paths=[]; d=start
    while d<=end: paths.append(day_path(d)); d+=timedelta(days=1)
    entries = [e for e in parse_entries(paths) if "[voice]" in e.marker]
    candidates = Counter()
    for e in entries:
        for m in re.findall(r"\b(?:[A-Z][a-zA-Z0-9&.-]+(?:\s+|$)){2,4}", e.text):
            s=" ".join(m.split()).strip()
            if s and s not in vocab and len(s) > 3: candidates[s]+=1
    if candidates:
        p=repo()/"config"/"vocab_suggestions.md"
        with p.open("a",encoding="utf-8") as f:
            f.write(f"\n## {start:%Y-%m-%d} to {end:%Y-%m-%d}\n")
            for s,c in candidates.most_common(20): f.write(f"- {s} ({c})\n")
        git_commit(f"vocab: suggestions {start:%Y-%m-%d}")


def retrieve(query: str, max_results: int = 8) -> str:
    init_repo(); q_terms=[t.lower() for t in re.findall(r"[\w'-]+", query) if len(t)>2]
    paths=sorted((repo()/"daily").glob("**/*.md"))
    entries=parse_entries(paths)
    scored=[]
    for idx,e in enumerate(entries):
        hay=(e.text+" "+e.marker).lower()
        exact=sum(3 for t in q_terms if t in hay)
        if not exact: continue
        intensity=2 if "!" in e.marker else 0
        scored.append((exact+intensity, idx, e))
    scored.sort(key=lambda x:(-x[0], x[1]))
    hits=[e for _,_,e in scored[:max_results]]
    if not hits:
        return f"No exact matches for: {query}"
    out=[f"Found {len(scored)} hit(s). Showing up to {max_results}.\n"]
    for e in hits:
        excerpt=" ".join(e.text.split())[:500]
        out.append(f"- {e.date} {e.time} {e.marker}\n  {excerpt}")
    span_days=len(set(e.date for _,_,e in scored))
    if len(scored)>20 or span_days>5:
        out.append("\nResults span enough material that I can synthesize this on demand. Underlying excerpts above remain the source of truth.")
    return "\n".join(out)


def is_retrieval_query(text: str) -> bool:
    s=text.strip().lower()
    return bool(re.match(r"^(what was i|what did i|surface|when did i|find|search|retrieve|anything i said|show me|where did i)", s))


def main(argv=None):
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    cap=sub.add_parser("capture"); cap.add_argument("--text", default=""); cap.add_argument("--kind", default="text"); cap.add_argument("--media", action="append", default=[]); cap.add_argument("--source", default="")
    rd=sub.add_parser("rollup"); rd.add_argument("--date")
    rp=sub.add_parser("replay"); rp.add_argument("--date")
    syn=sub.add_parser("synthesize"); syn.add_argument("kind", choices=["weekly","monthly","quarterly"])
    ret=sub.add_parser("retrieve"); ret.add_argument("query")
    args=ap.parse_args(argv)
    if args.cmd=="init": init_repo(); print(repo())
    elif args.cmd=="capture": print(append_entry(args.text, args.kind, args.media, args.source))
    elif args.cmd=="rollup": print(close_daily(date.fromisoformat(args.date) if args.date else None))
    elif args.cmd=="replay": print(read_daily(date.fromisoformat(args.date) if args.date else None))
    elif args.cmd=="synthesize": print(Path(synthesize(args.kind)).read_text(encoding="utf-8"))
    elif args.cmd=="retrieve": print(retrieve(args.query))

if __name__ == "__main__": main()
