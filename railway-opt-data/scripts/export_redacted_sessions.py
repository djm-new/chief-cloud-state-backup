#!/usr/bin/env python3
"""Export redacted session transcripts into the local thoughts repo.

The goal is to preserve conversational history for cloud backup while avoiding
raw secrets, tokens, and oversized duplicated prompt scaffolding.

Output layout:
  /opt/data/thoughts-repo/exports/sessions-redacted/YYYY/MM/<session_id>.md
  /opt/data/thoughts-repo/exports/sessions-redacted/index.md
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = Path("/opt/data/sessions")
DEFAULT_THOUGHTS_REPO = Path("/opt/data/thoughts-repo")
DEFAULT_OUT = DEFAULT_THOUGHTS_REPO / "exports" / "sessions-redacted"
DEFAULT_INDEX = DEFAULT_OUT / "index.md"

# Human-friendly Telegram topic names when we know them.
TOPIC_NAMES = {
    "1": "General",
    "3": "Archive",
    "4": "Briefings",
    "5": "Alerts",
    "6": "Daily Brain Dump",
    "7": "Coding 1",
    "8": "Coding 2",
}

SECRET_KEY_NAMES = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "XAI_API_KEY",
    "HF_TOKEN",
    "MINIMAX_API_KEY",
    "KIMI_API_KEY",
    "DASHSCOPE_API_KEY",
    "GLM_API_KEY",
    "COPILOT_GITHUB_TOKEN",
    "VOICE_TOOLS_OPENAI_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "TELEGRAM_BOT_TOKEN",
)

REDACTIONS = [
    # GitHub URL with embedded token.
    (re.compile(r"https://x-access-token:[^@\s]+@github\.com", re.I),
     "https://x-access-token:REDACTED@github.com"),
    # Explicit bearer tokens.
    (re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b", re.I), "Bearer REDACTED"),
    # Common env-style secrets.
    (re.compile(rf"\b({'|'.join(SECRET_KEY_NAMES)})\s*=\s*\S+", re.I),
     lambda m: f"{m.group(1)}=REDACTED"),
    # Common JSON-ish secret fields.
    (re.compile(r"(?i)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|password)\b\s*[:=]\s*)(['\"]?)[^,'\"\s}]+(\2)"),
     lambda m: f"{m.group(1)}{m.group(2)}REDACTED{m.group(3)}"),
    # Email addresses.
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    # Phone numbers / MSISDN-ish strings.
    (re.compile(r"(?<!\w)(?:\+?\d[\d\-\s().]{7,}\d)(?!\w)"), "[REDACTED_PHONE]"),
]

MAX_MESSAGE_CHARS = 6000
MAX_TOOL_OUTPUT_CHARS = 3500
MAX_INDEX_ENTRIES = 10_000


def redact_text(text: str) -> str:
    out = text
    for pattern, replacement in REDACTIONS:
        out = pattern.sub(replacement, out)
    return out


def fence(text: str) -> str:
    safe = text.replace("```", "``\u200b`")
    return f"```text\n{safe}\n```"


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    extra = len(text) - limit
    return text[:limit] + f"\n\n[truncated {extra} chars]"


def redacted_string(value: Any, *, limit: int = MAX_MESSAGE_CHARS) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            value = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
        except TypeError:
            value = str(value)
    elif not isinstance(value, str):
        value = str(value)
    return truncate(redact_text(value), limit)


def load_sessions_index(source: Path) -> dict[str, dict[str, Any]]:
    idx_path = source / "sessions.json"
    if not idx_path.exists():
        return {}
    try:
        data = json.loads(idx_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    index: dict[str, dict[str, Any]] = {}
    for record in data.values():
        session_id = record.get("session_id")
        if session_id:
            index[str(session_id)] = record
    return index


def parse_session_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[export-redacted-sessions] skip {path.name}: {exc}")
        return None
    if not isinstance(data, dict) or "messages" not in data:
        return None
    return data


def session_topic_name(meta: dict[str, Any]) -> str | None:
    origin = (meta or {}).get("origin") or {}
    thread_id = origin.get("thread_id")
    if thread_id is None:
        return None
    return TOPIC_NAMES.get(str(thread_id), f"thread {thread_id}")


def render_message(msg: dict[str, Any], *, max_output_chars: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    role = msg.get("role", "unknown")
    lines = [f"### {role}"]

    content = msg.get("content")
    if isinstance(content, str):
        body = redacted_string(content, limit=MAX_MESSAGE_CHARS)
        if body:
            lines.append(fence(body))

    tool_calls = msg.get("tool_calls") or []
    if tool_calls:
        lines.append("_Tool calls_")
        for call in tool_calls:
            fn = (call.get("function") or {}).get("name", "unknown")
            args = (call.get("function") or {}).get("arguments", "")
            args_redacted = redacted_string(args, limit=max_output_chars)
            lines.append(f"- `{fn}`")
            lines.append(fence(args_redacted))

    if msg.get("finish_reason"):
        lines.append(f"_finish_reason: `{msg['finish_reason']}`_")

    if msg.get("tool_call_id"):
        lines.append(f"_tool_call_id: `{msg['tool_call_id']}`_")

    if msg.get("reasoning") or msg.get("reasoning_content") or msg.get("codex_reasoning_items"):
        lines.append("_Reasoning items omitted in export (encrypted / internal)._" )

    return "\n\n".join(lines).strip() + "\n"


def render_session(session_path: Path, session: dict[str, Any], meta: dict[str, Any] | None) -> str:
    sid = str(session.get("session_id") or session_path.stem)
    model = session.get("model", "")
    platform = session.get("platform", "")
    start = session.get("session_start", "")
    updated = session.get("last_updated", "")
    message_count = len(session.get("messages") or [])
    topic = session_topic_name(meta or {})
    origin = (meta or {}).get("origin") or {}
    display_name = (meta or {}).get("display_name") or ""
    user_name = origin.get("user_name") or ""
    chat_name = origin.get("chat_name") or ""
    thread_id = origin.get("thread_id")

    header = [
        f"# Session {sid}",
        "",
        "## Metadata",
        f"- model: `{model}`" if model else "- model: (unknown)",
        f"- platform: `{platform}`" if platform else "- platform: (unknown)",
        f"- session_start: `{start}`" if start else "- session_start: (unknown)",
        f"- last_updated: `{updated}`" if updated else "- last_updated: (unknown)",
        f"- messages: `{message_count}`",
    ]
    if display_name:
        header.append(f"- display_name: `{display_name}`")
    if chat_name:
        header.append(f"- chat_name: `{chat_name}`")
    if user_name:
        header.append(f"- user_name: `{user_name}`")
    if thread_id is not None:
        header.append(f"- topic: `{topic}`" if topic else f"- topic: `thread {thread_id}`")
    header.extend([
        "",
        "> System prompt and tool schema are omitted from this export; the live system prompt lives in the Hermes skill set.",
        "",
        "## Transcript",
        "",
    ])

    body = []
    for msg in session.get("messages") or []:
        body.append(render_message(msg))

    return "\n".join(header + body).rstrip() + "\n"


def build_index(entries: list[dict[str, Any]]) -> str:
    lines = [
        "# Redacted session exports",
        "",
        "Generated from `/opt/data/sessions/` and safe for cloud backup.",
        "",
        "## Sessions",
        "",
    ]
    for entry in entries:
        lines.append(
            f"- `{entry['session_id']}` | `{entry['date']}` | `{entry['model']}` | `{entry['platform']}`"
            + (f" | `{entry['topic']}`" if entry.get('topic') else "")
            + f" | `{entry['message_count']}` messages | `{entry['path']}`"
        )
    if not entries:
        lines.append("- (no sessions exported yet)")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--repo", type=Path, default=DEFAULT_THOUGHTS_REPO)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    args = parser.parse_args()

    source = args.source
    out_dir = args.out
    index_path = args.index
    sessions_meta = load_sessions_index(source)

    exported: list[dict[str, Any]] = []
    failures: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean previous exports so the repo only contains current redacted history.
    for child in out_dir.glob("**/*"):
        if child.is_file() or child.is_symlink():
            child.unlink()
    for child in sorted([p for p in out_dir.glob("**/*") if p.is_dir()], reverse=True):
        # Remove empty directories from prior runs.
        try:
            child.rmdir()
        except OSError:
            pass

    for path in sorted(source.glob("*.json")):
        if path.name == "sessions.json":
            continue
        session = parse_session_file(path)
        if not session:
            continue
        sid = str(session.get("session_id") or path.stem)
        meta = sessions_meta.get(sid)
        try:
            rendered = render_session(path, session, meta)
            dt = session.get("session_start", "")[:10] or "unknown"
            if len(dt) == 10 and dt.count("-") == 2:
                year, month = dt[:4], dt[5:7]
            else:
                year, month = "unknown", "unknown"
            rel_dir = Path(year) / month
            target = out_dir / rel_dir / f"{sid}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
            exported.append({
                "session_id": sid,
                "date": dt,
                "model": session.get("model", ""),
                "platform": session.get("platform", ""),
                "topic": session_topic_name(meta or {}),
                "message_count": len(session.get("messages") or []),
                "path": str(target.relative_to(args.repo)),
            })
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")

    exported.sort(key=lambda e: (e["date"], e["session_id"]), reverse=True)
    if len(exported) > MAX_INDEX_ENTRIES:
        exported = exported[:MAX_INDEX_ENTRIES]

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(build_index(exported), encoding="utf-8")

    print(f"Exported {len(exported)} redacted sessions to {out_dir}")
    if failures:
        print(f"Skipped {len(failures)} session files:")
        for line in failures[:20]:
            print(f"- {line}")
        if len(failures) > 20:
            print(f"... and {len(failures) - 20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
