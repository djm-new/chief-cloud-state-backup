---
name: meeting-note-automation
description: "Use when automating meeting note, transcript, or call-summary export workflows from tools like Granola, Zoom, Teams, Google Meet, or local transcription apps. Covers discovery-first automation, destination/format confirmation, API-vs-UI fallback decisions, and preserving notes/transcripts into user-chosen storage."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [meetings, notes, transcripts, automation, windows, granola, export]
    related_skills: [google-workspace, teams-meeting-pipeline, ocr-and-documents]
---

# Meeting Note Automation

## Overview

Use this skill when the user wants to automate repetitive meeting-note workflows: exporting notes, transcripts, action items, summaries, or call records from a meeting app into files, Drive folders, docs, databases, or downstream workflows.

The key discipline is **discovery before scripting**. Do not jump directly to writing a script with assumed paths, file formats, or levels of automation. First determine what source data is available, what is blocked, and what outcome the user actually wants.

## When to Use

Use for:

- Automating export of meeting notes/transcripts from apps such as Granola, Zoom, Teams, Google Meet, Otter, Fathom, Fireflies, or local transcription tools.
- Turning copy/paste routines into scripts, hotkeys, scheduled jobs, or UI automation.
- Investigating whether a meeting app exposes data through local files, APIs, MCP, CLI tools, official exports, or browser/UI state.
- Creating stable output files in a user-selected folder.
- Building assisted workflows where the user still performs one or two manual copy steps but the script handles formatting and saving.
- Preparing DJ for upcoming meetings from calendar events, prior meeting notes, and related Slack/docs context; see `references/meeting-prep-memos.md`.
- Designing or generating meeting-prep memos from calendar events plus prior meeting notes, especially when the output must be brief, current-state-first, and action-oriented.

Do not use for:

- General summarization of already-provided meeting text; use normal writing/summarization behavior.
- Operating the existing Teams meeting summary pipeline; use `teams-meeting-pipeline` for that system.
- Editing Google Docs/Sheets/Drive directly; load `google-workspace` as well.

## First Principles

1. **Confirm the target outcome before implementing.** Ask for or verify:
   - destination folder or system
   - file format (`.txt`, `.md`, `.docx`, Google Doc, database row, etc.)
   - filename convention
   - whether the user wants assisted, hotkey, scheduled, or fully automatic export
   - whether transcripts are required, notes-only is acceptable, or both are mandatory

2. **Separate discovery from automation.** First identify what data path exists:
   - official API
   - official export
   - MCP connector
   - supported CLI
   - local plaintext cache/database
   - encrypted cache with supported decryptor
   - browser/app UI
   - clipboard/manual flow

3. **Prefer clean data access over UI automation.** API/official export/local structured data beats click automation when available.

4. **Fall back gradually.** If clean access fails, move to:
   - assisted clipboard workflow
   - hotkey workflow
   - UI automation with recorded selectors/clicks
   - scheduled background sync only after the user explicitly approves recurrence

5. **Avoid premature side effects.** Do not create files, scheduled tasks, login tokens, API keys, or recurring jobs until the user has confirmed scope.

## Discovery Checklist

Ask or inspect enough to answer:

- OS and app version.
- Where the app stores local data.
- Whether files are plaintext, database, or encrypted.
- Whether the user is logged in.
- Whether the user's plan supports API/transcript/export access.
- Whether official export includes transcripts.
- Whether the app can copy notes and transcript separately from its UI.
- Desired storage location and sync behavior.

For Windows local-app discovery, use PowerShell patterns like:

```powershell
$paths = @(
  "$env:APPDATA\AppName",
  "$env:LOCALAPPDATA\AppName",
  "$env:APPDATA\appname",
  "$env:LOCALAPPDATA\appname"
)

foreach ($p in $paths) {
  if (Test-Path $p) {
    Write-Host "FOUND: $p"
    Get-ChildItem $p -Recurse -File |
      Select-Object FullName, Length, LastWriteTime |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 20
  }
}
```

Do not ask the user to paste secrets, cookies, tokens, or full credential/cache file contents.

## Automation Levels

### Level A: Assisted Clipboard Export

Best first version when API/local parsing is uncertain.

Flow:

1. User starts script.
2. Script asks for meeting title/date if not detectable.
3. User copies notes and presses Enter.
4. Script captures clipboard.
5. User copies transcript and presses Enter.
6. Script writes formatted output to the confirmed destination.

This removes file creation, naming, formatting, and saving while staying robust.

### Level B: Hotkey-Assisted Export

Use AutoHotkey, Power Automate Desktop, or a small tray utility to trigger Level A from anywhere. Still relies on user-controlled copy steps.

### Level C: UI Automation

Use when the user wants minimal manual action and data access is blocked. Requires exact UI state and should be built from observed keyboard/click sequences or UI automation selectors.

Common Windows options:

- Power Automate Desktop for recorder-based workflows.
- AutoHotkey for hotkeys and clipboard orchestration.
- Python + pywinauto for selector-driven automation.

### Level D: API/Scheduled Export

Use only when a stable API/export endpoint is available and the user approves recurrence. Respect DJ's preference for explicit approval before recurring monitors.

## Meeting Prep Cards

When DJ asks for meeting prep (for example, “prep me for my next meeting” or asks for a concrete example), the output should be the actual short card he would read before entering the meeting — not a framework, implementation spec, or provenance-heavy research memo.

Use `references/meeting-prep-cards.md` for the full pattern. Key rules:

- Identify the actual calendar event first: title, ET time, duration, attendees, description/agenda availability.
- Check meeting notes, but classify evidence quality before using it as context.
- Do not infer the agenda from stale or weak note matches just because an attendee name appears.
- If context is weak, say that plainly and give DJ a sharp opening question plus branches to listen for.
- Optimize for: “Would DJ be sharper in the meeting after reading this?” If not, say less.

Preferred visible shape:

```markdown
## [time ET] [Meeting title]

**Bottom line:** [known/uncertain + posture]

**Walk in knowing**
- [1-3 useful facts only]

**DJ should**
- [1-3 concrete behaviors/questions]

**If nothing else, ask**
"[one sharp opening question]"
```

Anti-patterns:

- Producing a system design when the user asked for a meeting prep example.
- Overfitting one stale note and steering DJ toward a guessed agenda.
- Making the visible product about scoring, retrieval, source freshness, or implementation mechanics.
- Writing a confident-sounding memo from weak evidence.

## Meeting Prep Memos

When DJ asks to be prepared for a meeting, do not treat this as generic summarization. Follow `references/meeting-prep-memos.md`.

Required behavior:

1. Identify the actual calendar event, attendees by email, recurrence status, and same-day adjacent meetings.
2. If recurring, start with the prior occurrence and prior note; extract to-dos, follow-ups, unresolved decisions, and important highlights.
3. Verify whether follow-ups were actioned using later notes, Slack, or related docs before presenting them as still open.
4. Resolve who each participant is, especially unfamiliar names: internal/external, role, team, manager, start date, and recent topic-specific communications.
5. Resolve the meeting topic from title, description, agenda links, attendees, prior notes, and related docs. If agenda is unavailable or context is weak, say so and give DJ the sharp opening question rather than guessing.
6. Avoid repeating generic person history across multiple same-day meetings; include only context that changes how DJ should behave in this meeting.

Preferred output:

```markdown
## [time ET] Meeting name

**Bottom line:** [what this meeting likely is / how DJ should approach it]

**Know walking in**
- [relevant fact]
- [prior follow-up or current context]
- [risk/gap]

**DJ should**
- [specific action/question/posture]

**Ask**
“[single sharp question]”
```

Pitfall: never overfit to stale name matches. If a meeting includes `Zaid`, first resolve the actual attendee email/person before assuming an old note about another Zaid or an external deal is relevant.

## Output Design

Confirm before choosing defaults. Good defaults, if the user asks you to choose:

- Markdown (`.md`) for human-readable notes and searchable text.
- Filename: `yyyy-MM-dd - Meeting Title.md`.
- Include title/date/source sections.
- Separate sections for generated notes and transcript.

Example:

```markdown
# Meeting Title

Date: 2026-08-10
Source: Granola

---

## Notes

...

---

## Transcript

...
```

For DJ's Granola workflow on Windows, confirmed preferences are:

```text
Destination: H:\\\\My Drive\\\\Meeting_Notes
Filename: [Meeting Title] YYYY_MM_DD.txt
Separator before transcript: ***
Date: use the meeting date, not today's/export date
Automation level: DJ wants no-touch automation, not a clipboard-assisted flow, once the UI path is known
```

Still confirm any missing pieces before writing a script, especially whether the first no-touch version should export the currently open meeting, selected/highlighted meeting, or latest completed meeting.

### DJ meeting-prep memo design

When DJ asks for meeting preparation from calendar + prior notes, use `references/meeting-prep-memos.md`. Key defaults:

- canonical source: `dj@flow.life` → `My Drive / Meeting_Notes`, folder ID `1wpJT9Yuoah_gwAOR2crtw7vjG6z6GkUB`
- memo must be digestible in under 90 seconds; target 180–260 words, hard max 320
- all meeting times shown in ET
- required structure: title, `As of [ET timestamp]` source freshness, `Read this first`, `Current state`, `Needs DJ`, `Watching`, `Ask/posture`
- stale/missing/conflicting context must be visible in `Current state` or `Watching`
- use a builder → consumer-proxy → refiner loop up to 5 iterations for high-value prep; the consumer proxy should act as DJ and reject memos that lack usefulness, freshness, ET correctness, or action clarity
- no writes/sends/notifications/recurring jobs without explicit approval

## Granola Notes

Granola has changed storage formats over time. Older community tools often read plaintext local cache files. Newer installs may use encrypted files, for example:

```text
cache-v6.json.enc
supabase.json.enc
stored-accounts.json.enc
```

If a CLI expects plaintext `supabase.json` but only `supabase.json.enc` exists, do not declare Granola impossible to automate. Treat that specific CLI path as blocked and evaluate:

- current official API access
- MCP connector access
- plan restrictions around transcript access
- official CSV export
- assisted clipboard workflow
- UI automation

See `references/granola-windows.md` for the Windows-specific observations captured from a real troubleshooting session.

## Common Pitfalls

1. **Jumping straight to a script with assumed paths.** Always ask/confirm the output folder, format, and naming convention first. The user may have a synced folder or existing filing system.

2. **Over-automating before validating access.** A fragile UI bot is not the first move if an API or export is available.

3. **Treating encrypted local files as a dead end.** Encryption blocks naive parsing, not all automation. Move to API/MCP/export/clipboard/UI options.

4. **Asking for sensitive file contents.** Do not request full token, cookie, cache, or credential files. If file-shape diagnostics are needed, ask only for paths, sizes, timestamps, or non-sensitive headers.

5. **Creating recurring jobs too early.** Scheduling exports or background watchers requires explicit user approval.

6. **Not explaining the decision tree.** If the user signals confusion or says to slow down, stop making leaps and explain what was learned, why a path is blocked, and what choices remain.

## Verification Checklist

- [ ] Source data path identified or explicitly classified as blocked.
- [ ] Destination folder confirmed.
- [ ] File format confirmed.
- [ ] Filename convention confirmed.
- [ ] Notes/transcript requirements confirmed.
- [ ] User approved any side effects before files/tasks/scripts were created.
- [ ] Script or workflow tested with sample content before claiming success.
- [ ] Sensitive credential/cache content was not requested or exposed.
