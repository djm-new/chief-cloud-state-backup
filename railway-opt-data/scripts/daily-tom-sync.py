#!/usr/bin/env python3
"""Google-native Daily ToM sync for DJ.

Replaces the old Notion-backed daily-sync for the core Google Doc workflow:
- Fetch structured Google Doc content
- Find latest dated section near top
- Carry forward active tasks
- Strip in-progress markers on rollover
- Mark completed tasks with ✅ in the source day and drop them from rollover
- Handle simple parking markers
- Maintain lightweight task_state.json
- Insert a new dated section after [Next date] / Parking Lot

Default mode is dry-run. Use --apply to write to the Google Doc.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import string
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

DOC_ID = "10KsXkvIR0Je4J_dGkv0PI-4Mngb5db3MSstjnEU8Gpw"
STATE_DIR = Path("/opt/data/daily-tom")
STATE_PATH = STATE_DIR / "task_state.json"
SLACK_INTAKE_PATH = STATE_DIR / "slack_intake.json"
SLACK_INTAKE_STATE_PATH = STATE_DIR / "slack_intake_state.json"
DEFAULT_HERMES_HOME = "/opt/data/google-accounts/personal"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
]

DATE_RE = re.compile(
    r"^(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)\s+\d{1,2},\s+\d{4}(?:\s+-\s+Week Ahead)?$"
)
SECTION_RE = re.compile(r"^\[(.+?)\]$")
ID_RE = re.compile(r"\[n:([A-Za-z0-9]{4,12})\]")
REL_PARK_RE = re.compile(r"\[(\d{1,3})d\]")
ABS_PARK_RE = re.compile(r"\[(\d{1,2})/(\d{1,2})\]")
# DJ shorthand: typing a leading `x` or `>` in the Google Doc should be
# treated as the emoji marker on the next sync/cleanup pass. Be conservative
# with bare `x`: accept lowercase `xTask` / `x Task`, but do not treat
# uppercase task names like `XM comp` as done.
DONE_PREFIX_RE = re.compile(r"^(?:✅\s*|\[x\]\s*|[xX]\s+|x(?=[A-Z0-9]))")
PROGRESS_PREFIX_RE = re.compile(r"^(?:↗️\s*|\[>\]\s*|>\s*)")
PRIORITY_RE = re.compile(r"(?<!\*)\*{1,3}(?!\*)")

GROUP_ORDER = ["Professional", "Professional - MENA", "Professional - Others", "Personal"]


@dataclass
class Para:
    text: str
    start: int
    end: int


@dataclass
class Task:
    text: str
    group: str
    id: str
    priority: int = 0
    original_order: int = 0
    first_seen: str | None = None
    last_seen: str | None = None
    status: str = "active"


def get_creds(hermes_home: str) -> Credentials:
    token_path = Path(hermes_home) / "google_token.json"
    if not token_path.exists():
        raise SystemExit(f"Missing Google token: {token_path}")
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        os.chmod(token_path, 0o600)
    return creds


def extract_paragraphs(doc: dict[str, Any]) -> list[Para]:
    out: list[Para] = []
    for el in doc.get("body", {}).get("content", []):
        para = el.get("paragraph")
        if not para:
            continue
        text = ""
        for pe in para.get("elements", []):
            tr = pe.get("textRun")
            if tr:
                text += tr.get("content", "")
        # Google paragraph text normally ends with newline. Keep indexes but strip line ending for logic.
        out.append(Para(text=text.rstrip("\n"), start=el.get("startIndex", 0), end=el.get("endIndex", 0)))
    return out


def is_date_line(text: str) -> bool:
    return bool(DATE_RE.match(text.strip()))


def find_sections(paras: list[Para]) -> tuple[int, int, int | None, int | None, list[int]]:
    next_idx = next((i for i, p in enumerate(paras) if p.text.strip() == "[Next date]"), None)
    if next_idx is None:
        raise SystemExit("Could not find [Next date] marker")
    date_idxs = [i for i, p in enumerate(paras) if is_date_line(p.text)]
    if not date_idxs:
        raise SystemExit("Could not find any dated section")
    latest_idx = date_idxs[0]
    next_date_idx = date_idxs[1] if len(date_idxs) > 1 else len(paras)

    parking_idx = next((i for i, p in enumerate(paras) if p.text.strip() == "[Parking Lot]"), None)
    parking_end = None
    if parking_idx is not None:
        # Parking lot lives before first date if present.
        parking_end = latest_idx
    return next_idx, latest_idx, next_date_idx, parking_idx, parking_end, date_idxs


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"tasks": {}, "runs": []}


def load_slack_intake() -> tuple[list[Task], list[dict[str, Any]]]:
    """Load Slack→ToM candidates produced by daily-tom-slack-extract.py.

    Returns Task objects plus raw item dicts. Deduping is handled by source_url
    persisted in slack_intake_state.json after successful apply.
    """
    if not SLACK_INTAKE_PATH.exists():
        return [], []
    try:
        payload = json.loads(SLACK_INTAKE_PATH.read_text())
    except Exception:
        return [], []
    try:
        intake_state = json.loads(SLACK_INTAKE_STATE_PATH.read_text()) if SLACK_INTAKE_STATE_PATH.exists() else {"seen_urls": []}
    except Exception:
        intake_state = {"seen_urls": []}
    seen = set(intake_state.get("seen_urls", []))
    tasks: list[Task] = []
    raw_items: list[dict[str, Any]] = []
    for i, item in enumerate(payload.get("items") or []):
        url = item.get("source_url") or ""
        if url and url in seen:
            continue
        text = item.get("task_text") or ""
        task_id = item.get("id") or None
        group = item.get("group") or "Professional - Others"
        if not text or not task_id or group not in GROUP_ORDER:
            continue
        _, _, _, priority, parsed_id, _ = clean_task_line(text)
        tasks.append(Task(text=text, group=group, id=parsed_id or task_id, priority=priority, original_order=10_000 + i))
        raw_items.append(item)
    return tasks, raw_items


def mark_slack_intake_seen(raw_items: list[dict[str, Any]]) -> None:
    if not raw_items:
        return
    try:
        state = json.loads(SLACK_INTAKE_STATE_PATH.read_text()) if SLACK_INTAKE_STATE_PATH.exists() else {"seen_urls": []}
    except Exception:
        state = {"seen_urls": []}
    seen = list(dict.fromkeys(list(state.get("seen_urls", [])) + [x.get("source_url") for x in raw_items if x.get("source_url")]))
    state["seen_urls"] = seen[-5000:]
    state["updated_at"] = dt.datetime.utcnow().isoformat() + "Z"
    SLACK_INTAKE_STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True))
    os.chmod(SLACK_INTAKE_STATE_PATH, 0o600)


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    os.replace(tmp, STATE_PATH)
    os.chmod(STATE_PATH, 0o600)


def gen_id(existing: set[str]) -> str:
    alphabet = "0123456789abcdef"
    while True:
        x = "".join(random.choice(alphabet) for _ in range(5))
        if x not in existing:
            return x


def clean_task_line(line: str) -> tuple[str, bool, bool, int, str | None, int | None]:
    t = line.strip()
    is_done = bool(DONE_PREFIX_RE.match(t))
    is_progress = bool(PROGRESS_PREFIX_RE.match(t))
    t = DONE_PREFIX_RE.sub("", t)
    t = PROGRESS_PREFIX_RE.sub("", t)
    park_days = None
    m = REL_PARK_RE.search(t)
    if m:
        park_days = int(m.group(1))
        t = REL_PARK_RE.sub("", t).strip()
    id_match = ID_RE.search(t)
    task_id = id_match.group(1) if id_match else None
    priority = 0
    for pm in PRIORITY_RE.finditer(t):
        priority = max(priority, len(pm.group(0)))
    t = re.sub(r"\s+", " ", t).strip()
    return t, is_done, is_progress, priority, task_id, park_days


def completion_replace_request(raw_line: str, clean_text: str) -> dict[str, Any]:
    """Replace a completed task's leading x/[x] with ✅ in the source doc."""
    return {
        "replaceAllText": {
            "containsText": {"text": raw_line, "matchCase": True},
            "replaceText": f"✅ {clean_text}",
        }
    }


def progress_replace_request(raw_line: str, clean_text: str) -> dict[str, Any]:
    """Replace a task's leading > with ↗️ in the source doc."""
    return {
        "replaceAllText": {
            "containsText": {"text": raw_line, "matchCase": True},
            "replaceText": f"↗️ {clean_text}",
        }
    }


def infer_group(current_section: str | None, task_text: str) -> str | None:
    if current_section in GROUP_ORDER:
        return current_section
    if task_text.startswith("MENA:"):
        return "Professional - MENA"
    if re.match(r"^[A-Za-z0-9 &/+-]+:", task_text):
        return "Professional - Others"
    return current_section


def parse_tasks(paras: list[Para], start_idx: int, end_idx: int, today: dt.date, state: dict[str, Any]) -> tuple[list[Task], list[str], list[dict[str, Any]], list[str], list[Task]]:
    tasks: list[Task] = []
    completed: list[str] = []
    completed_replacements: list[dict[str, Any]] = []
    in_progress: list[str] = []
    in_progress_replacements: list[dict[str, Any]] = []
    newly_parked: list[Task] = []
    section = None
    existing_ids = set(state.get("tasks", {}).keys())
    order = 0
    for p in paras[start_idx + 1 : end_idx]:
        raw = p.text.strip()
        if not raw:
            continue
        sm = SECTION_RE.match(raw)
        if sm:
            section = sm.group(1)
            continue
        if is_date_line(raw) or raw == "[Next date]" or raw == "[Parking Lot]":
            continue
        group = infer_group(section, raw)
        if group not in GROUP_ORDER:
            continue
        text, is_done, is_prog, priority, task_id, park_days = clean_task_line(raw)
        if not text:
            continue
        if task_id is None:
            task_id = gen_id(existing_ids)
            existing_ids.add(task_id)
            if "[n:" not in text:
                text = f"{text} [n:{task_id}]"
        if is_done:
            completed.append(task_id)
            completed_replacements.append(completion_replace_request(raw, text))
            state.setdefault("tasks", {}).setdefault(task_id, {})
            state["tasks"][task_id].update({"text": re.sub(ID_RE, "", text).strip(), "group": group, "status": "completed", "completed_date": today.isoformat(), "last_seen": today.isoformat(), "priority": priority})
            continue
        if is_prog:
            in_progress.append(task_id)
            in_progress_replacements.append(progress_replace_request(raw, text))
            if not PROGRESS_PREFIX_RE.match(text):
                text = f"↗️ {text}"
        task = Task(text=text, group=group, id=task_id, priority=priority, original_order=order)
        order += 1
        if park_days is not None:
            return_date = today + dt.timedelta(days=park_days)
            task.text = REL_PARK_RE.sub("", task.text).strip()
            task.text = f"[{return_date.month}/{return_date.day}] {task.text}"
            newly_parked.append(task)
            continue
        tasks.append(task)
    return tasks, completed, completed_replacements, in_progress, in_progress_replacements, newly_parked


def parse_parking(paras: list[Para], parking_idx: int | None, parking_end: int | None, today: dt.date) -> tuple[list[Task], list[str]]:
    if parking_idx is None or parking_end is None:
        return [], []
    returning: list[Task] = []
    staying: list[str] = []
    section = None
    order = 0
    for p in paras[parking_idx + 1 : parking_end]:
        raw = p.text.strip()
        if not raw:
            staying.append("")
            continue
        sm = SECTION_RE.match(raw)
        if sm:
            section = sm.group(1)
            staying.append(raw)
            continue
        m = ABS_PARK_RE.match(raw)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            return_date = dt.date(today.year, month, day)
            if return_date <= today:
                text = ABS_PARK_RE.sub("", raw, count=1).strip()
                _, _, _, priority, task_id, _ = clean_task_line(text)
                if task_id:
                    returning.append(Task(text=text, group=infer_group(section, text) or "Professional", id=task_id, priority=priority, original_order=order))
                    order += 1
                    continue
        staying.append(raw)
    return returning, staying


def priority_sort_key(t: Task) -> tuple[int, int]:
    # Higher priority first, preserve prior order within tier.
    return (-t.priority, t.original_order)


def build_section(today: dt.date, carried: list[Task], returning: list[Task], state: dict[str, Any]) -> str:
    all_tasks = carried + returning
    lines: list[str] = [today.strftime("%B %-d, %Y") if sys.platform != "win32" else today.strftime("%B %#d, %Y")]
    by_group = {g: [] for g in GROUP_ORDER}
    for t in all_tasks:
        by_group.setdefault(t.group, []).append(t)
        clean_text = re.sub(ID_RE, "", t.text).strip()
        state.setdefault("tasks", {}).setdefault(t.id, {})
        existing = state["tasks"][t.id]
        existing.update({
            "text": clean_text,
            "group": t.group,
            "status": "active",
            "last_seen": today.isoformat(),
            "priority": t.priority,
        })
        existing.setdefault("first_seen", today.isoformat())
    for group in GROUP_ORDER:
        lines.append("")
        lines.append(f"[{group}]")
        for task in sorted(by_group.get(group, []), key=priority_sort_key):
            # Ensure completed and in-progress markers are stripped on rollover.
            text = DONE_PREFIX_RE.sub("", task.text)
            text = PROGRESS_PREFIX_RE.sub("", text).strip()
            if "[n:" not in text:
                text = f"{text} [n:{task.id}]"
            lines.append(text)
    lines.append("")
    return "\n".join(lines)


def style_requests_for_inserted_section(start_index: int, text: str) -> list[dict[str, Any]]:
    """Make a newly inserted day match the existing Daily ToM doc style.

    Google Docs insertText inherits the paragraph style at the insertion point.
    Because we insert directly after [Next date], that can cause the entire new
    section to inherit Heading 2. The desired format is: date heading = Heading 2,
    all section labels/tasks/blanks = Normal text.
    """
    requests: list[dict[str, Any]] = []
    idx = start_index
    for line_no, line in enumerate(text.splitlines(keepends=True)):
        end = idx + len(line)
        if end > idx:
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": "HEADING_2" if line_no == 0 else "NORMAL_TEXT"},
                    "fields": "namedStyleType",
                }
            })
        idx = end
    return requests


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Write the new section to Google Docs")
    ap.add_argument("--date", help="YYYY-MM-DD override; defaults to today")
    ap.add_argument("--account-home", default=DEFAULT_HERMES_HOME)
    ap.add_argument("--doc-id", default=DOC_ID)
    ap.add_argument("--include-slack-suggestions", action="store_true", help="Include precomputed Slack suggestions in the new ToM section. Do not use without DJ's explicit approval.")
    args = ap.parse_args()

    today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    creds = get_creds(args.account_home)
    docs = build("docs", "v1", credentials=creds, cache_discovery=False)
    doc = docs.documents().get(documentId=args.doc_id).execute()
    paras = extract_paragraphs(doc)
    next_idx, latest_idx, next_date_idx, parking_idx, parking_end, date_idxs = find_sections(paras)

    today_label = today.strftime("%B %-d, %Y") if sys.platform != "win32" else today.strftime("%B %#d, %Y")
    if any(p.text.strip() == today_label for p in paras[: max(80, next_date_idx + 5)]):
        print(json.dumps({"status": "noop", "reason": f"Section already exists for {today_label}", "date": today.isoformat()}, indent=2))
        return 0

    state = load_state()
    carried, completed, completed_replacements, in_progress, in_progress_replacements, newly_parked = parse_tasks(paras, latest_idx, next_date_idx, today, state)
    returning, staying_parked = parse_parking(paras, parking_idx, parking_end, today)
    slack_tasks, slack_raw_items = (load_slack_intake() if args.include_slack_suggestions else ([], []))
    new_section = build_section(today, carried + slack_tasks, returning, state)

    # Insert after [Next date] paragraph, or after parking lot if present before latest date.
    insertion_index = paras[next_idx].end
    if parking_idx is not None and parking_end is not None and parking_idx < latest_idx:
        # Preserve parking lot at top: insert after parking lot, before latest dated section.
        insertion_index = paras[parking_end - 1].end if parking_end > parking_idx + 1 else paras[parking_idx].end

    inserted_text = new_section + "\n"
    requests = [{"insertText": {"location": {"index": insertion_index}, "text": inserted_text}}]
    requests.extend(style_requests_for_inserted_section(insertion_index, inserted_text))
    requests.extend(in_progress_replacements)
    requests.extend(completed_replacements)

    summary = {
        "status": "dry_run" if not args.apply else "applied",
        "date": today.isoformat(),
        "doc_title": doc.get("title"),
        "latest_source_section": paras[latest_idx].text.strip(),
        "insert_index": insertion_index,
        "counts": {
            "carried": len(carried),
            "slack_added": len(slack_tasks),
            "returning_from_parking": len(returning),
            "newly_parked_from_latest": len(newly_parked),
            "completed_seen": len(completed),
            "in_progress_seen": len(in_progress),
        },
        "by_group": {g: sum(1 for t in carried + returning + slack_tasks if t.group == g) for g in GROUP_ORDER},
        "slack_items": [{"id": x.get("id"), "channel": x.get("channel"), "score": x.get("score"), "source_url": x.get("source_url")} for x in slack_raw_items],
        "new_section": new_section,
    }

    if args.apply:
        docs.documents().batchUpdate(documentId=args.doc_id, body={"requests": requests}).execute()
        state.setdefault("runs", []).append({k: v for k, v in summary.items() if k != "new_section"})
        save_state(state)
        mark_slack_intake_seen(slack_raw_items)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
