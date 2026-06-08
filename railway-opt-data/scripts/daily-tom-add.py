#!/opt/data/google-accounts/.venv/bin/python
"""Add a single item to DJ's active Daily ToM Google Doc section.

Designed for low-friction Telegram commands such as:
  add to top of mind "XM comp check"

Default behavior:
- writes to the latest dated section in the Daily ToM Google Doc;
- infers group from prefixes (Personal:, MENA:) or defaults to Professional;
- inserts near the top of the chosen group;
- adds a stable [n:xxxxx] id used by the daily carry-forward sync;
- exits with JSON suitable for gateway confirmation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

DOC_ID = "10KsXkvIR0Je4J_dGkv0PI-4Mngb5db3MSstjnEU8Gpw"
STATE_DIR = Path("/opt/data/daily-tom")
STATE_PATH = STATE_DIR / "task_state.json"
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
GROUP_ORDER = ["Professional", "Professional - MENA", "Professional - Others", "Personal"]
PERSONAL_HINTS = (
    r"\bticket(s)?\b",
    r"\bflight(s)?\b",
    r"\bhotel(s)?\b",
    r"\btravel\b",
    r"\btrip\b",
    r"\bbook\b.*\b(ticket|flight|hotel|travel|trip)\b",
)


@dataclass
class Para:
    text: str
    start: int
    end: int


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
        out.append(Para(text=text.rstrip("\n"), start=el.get("startIndex", 0), end=el.get("endIndex", 0)))
    return out


def is_date_line(text: str) -> bool:
    return bool(DATE_RE.match(text.strip()))


def normalize_task_text(text: str) -> str:
    text = re.sub(ID_RE, "", text or "")
    text = re.sub(r"^(?:\*\s*|!\s*|✅\s*|\[x\]\s*|[xX]\s+|x(?=[A-Z0-9])|↗️\s*|\[>\]\s*|>\s*)", "", text.strip())
    return re.sub(r"\s+", " ", text).strip()


def infer_group(raw_text: str, explicit_group: str | None = None) -> tuple[str, str]:
    text = raw_text.strip()
    if explicit_group:
        group = explicit_group.strip()
        if group not in GROUP_ORDER:
            raise SystemExit(f"Unsupported group: {group}. Expected one of: {', '.join(GROUP_ORDER)}")
        return group, text

    # Useful shorthand from Telegram: "personal: ..." and "mena: ...".
    m = re.match(r"^(personal|private):\s*(.+)$", text, flags=re.I)
    if m:
        return "Personal", m.group(2).strip()
    if re.match(r"^mena:\s*", text, flags=re.I):
        cleaned = re.sub(r"^mena:\s*", "MENA: ", text, flags=re.I).strip()
        return "Professional - MENA", cleaned
    m = re.match(r"^(other|others):\s*(.+)$", text, flags=re.I)
    if m:
        return "Professional - Others", m.group(2).strip()
    if any(re.search(pattern, text, flags=re.I) for pattern in PERSONAL_HINTS):
        return "Personal", text
    return "Professional", text


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"tasks": {}, "runs": []}


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


def existing_ids(paras: list[Para]) -> set[str]:
    ids: set[str] = set()
    for p in paras:
        ids.update(m.group(1) for m in ID_RE.finditer(p.text))
    state = load_state()
    ids.update((state.get("tasks") or {}).keys())
    return ids


def latest_section_bounds(paras: list[Para]) -> tuple[int, int]:
    date_idxs = [i for i, p in enumerate(paras) if is_date_line(p.text)]
    if not date_idxs:
        raise SystemExit("Could not find any dated Daily ToM section")
    latest_idx = date_idxs[0]
    end_idx = date_idxs[1] if len(date_idxs) > 1 else len(paras)
    return latest_idx, end_idx


def find_group_insert(paras: list[Para], start_idx: int, end_idx: int, group: str, append_to_bottom: bool = True) -> tuple[int, bool]:
    """Return (Google Docs insertion index, group_exists).

    By default new items are appended to the bottom of the group.
    """
    group_line = f"[{group}]"
    group_heading_idx = None
    for i in range(start_idx + 1, end_idx):
        if paras[i].text.strip() == group_line:
            group_heading_idx = i
            break

    if group_heading_idx is not None:
        if not append_to_bottom:
            # Insert immediately after the heading paragraph so priority items stay at the top.
            return paras[group_heading_idx].end, True

        # Walk forward until the next section heading or date line, so we can append to the bottom.
        last_content_idx = group_heading_idx
        for j in range(group_heading_idx + 1, end_idx):
            raw = paras[j].text.strip()
            if is_date_line(raw) or SECTION_RE.match(raw):
                break
            if raw:
                last_content_idx = j

        return paras[last_content_idx].end, True

    # Group missing: add heading near the end of the current dated section.
    # Insert before the next date section when possible.
    insertion = paras[end_idx - 1].end if end_idx > start_idx + 1 else paras[start_idx].end
    return insertion, False


def is_priority_item(raw_text: str) -> bool:
    text = raw_text.strip()
    return text.startswith(("*", "!"))


def current_group_items(paras: list[Para], start_idx: int, end_idx: int, group: str) -> list[str]:
    items: list[str] = []
    in_group = False
    for p in paras[start_idx + 1 : end_idx]:
        raw = p.text.strip()
        sm = SECTION_RE.match(raw)
        if sm:
            in_group = sm.group(1) == group
            continue
        if in_group and raw and not is_date_line(raw):
            items.append(normalize_task_text(raw).lower())
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="Task text to add")
    ap.add_argument("--text", dest="text_opt", help="Task text to add")
    ap.add_argument("--group", choices=GROUP_ORDER, help="Target Daily ToM group")
    ap.add_argument("--apply", action="store_true", help="Write to Google Docs; without this, dry-run only")
    ap.add_argument("--account-home", default=DEFAULT_HERMES_HOME)
    ap.add_argument("--doc-id", default=DOC_ID)
    args = ap.parse_args()

    raw_text = (args.text_opt or args.text or "").strip().strip('"“”')
    if not raw_text:
        raise SystemExit("Missing ToM item text")

    group, task_text = infer_group(raw_text, args.group)
    task_text = normalize_task_text(task_text)
    if not task_text:
        raise SystemExit("Missing ToM item text after cleanup")

    priority = is_priority_item(raw_text)

    creds = get_creds(args.account_home)
    docs = build("docs", "v1", credentials=creds, cache_discovery=False)
    doc = docs.documents().get(documentId=args.doc_id).execute()
    paras = extract_paragraphs(doc)
    latest_idx, end_idx = latest_section_bounds(paras)
    date_label = paras[latest_idx].text.strip()

    if task_text.lower() in current_group_items(paras, latest_idx, end_idx, group):
        print(json.dumps({"status": "already_present", "item": task_text, "group": group, "date_label": date_label}, ensure_ascii=False))
        return 0

    task_id = gen_id(existing_ids(paras))
    line = f"{task_text} [n:{task_id}]\n"
    insertion_index, group_exists = find_group_insert(paras, latest_idx, end_idx, group, append_to_bottom=not priority)
    inserted_text = line if group_exists else f"\n[{group}]\n{line}"
    summary = {
        "status": "dry_run" if not args.apply else "applied",
        "item": task_text,
        "group": group,
        "id": task_id,
        "date_label": date_label,
        "doc_title": doc.get("title"),
        "insert_index": insertion_index,
    }

    if args.apply:
        docs.documents().batchUpdate(
            documentId=args.doc_id,
            body={"requests": [{"insertText": {"location": {"index": insertion_index}, "text": inserted_text}}]},
        ).execute()
        state = load_state()
        today = dt.date.today().isoformat()
        state.setdefault("tasks", {}).setdefault(task_id, {}).update({
            "text": task_text,
            "group": group,
            "status": "active",
            "first_seen": today,
            "last_seen": today,
            "priority": 0,
        })
        state.setdefault("manual_additions", []).append({
            "id": task_id,
            "text": task_text,
            "group": group,
            "date_label": date_label,
            "added_at": dt.datetime.utcnow().isoformat() + "Z",
            "source": "daily-tom-add.py",
        })
        save_state(state)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
