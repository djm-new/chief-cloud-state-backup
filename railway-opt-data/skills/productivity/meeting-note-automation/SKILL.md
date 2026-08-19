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
Destination: H:\\My Drive\\Meeting_Notes
Filename: [Meeting Title] YYYY_MM_DD.txt
Separator before transcript: ***
Date: use the meeting date, not today's/export date
Automation level: DJ wants no-touch automation, not a clipboard-assisted flow, once the UI path is known
```

Still confirm any missing pieces before writing a script, especially whether the first no-touch version should export the currently open meeting, selected/highlighted meeting, or latest completed meeting.

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
