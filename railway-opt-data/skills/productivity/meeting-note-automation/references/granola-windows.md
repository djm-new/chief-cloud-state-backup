# Granola on Windows: Export Automation Notes

## Scenario

User had Granola open on Windows and wanted to avoid a repeated free-plan workflow:

1. Create a text file.
2. Copy notes from Granola.
3. Paste notes.
4. Copy transcript from Granola.
5. Paste transcript.
6. Save file.

## Local Data Observed

PowerShell discovery found Granola data in both casing variants:

```text
C:\Users\DJ\AppData\Roaming\Granola
C:\Users\DJ\AppData\Local\Granola
C:\Users\DJ\AppData\Roaming\granola
C:\Users\DJ\AppData\Local\granola
```

Important files observed under Roaming:

```text
cache-v6.json.enc
supabase.json.enc
stored-accounts.json.enc
user-preferences.json.enc
IndexedDB\app_ui_0.indexeddb.leveldb\000004.log
Local Storage\leveldb\*.ldb
Network\Cookies
```

The `.enc` files indicate newer encrypted local storage. Do not assume older cache-based exporters can read it directly.

## CLI Attempt

The npm package `granola-cli` was installed/current at:

```text
0.2.0
```

`granola auth login` failed with:

```text
Error: Could not load credentials.
Expected file at: C:\Users\DJ\AppData\Roaming\Granola\supabase.json

Make sure the Granola desktop app is installed and you are logged in.
```

Interpretation: that CLI expected the older plaintext `supabase.json`; this install only had `supabase.json.enc`. Treat that CLI path as blocked unless a newer tool/version supports encrypted Windows storage.

## Official/Research Findings

Granola docs describe:

- Historical export via Settings → Profile → Generate CSV.
- CSV includes title, note summary, transcript, and basic details.
- Export link is emailed and expires after 24 hours.
- Only one export can be generated every 24 hours.

Granola MCP docs describe:

- Browser OAuth authentication.
- Free/Basic MCP access to personal notes from the last 30 days.
- Some folder/search/transcript tools may be paid-plan-only.
- Public MCP endpoint: `https://mcp.granola.ai/mcp`.

Granola API docs describe:

- Personal API keys via Settings → Connectors → API keys.
- Bearer auth against `https://public-api.granola.ai/v1/notes`.
- `include=transcript` can return transcript when supported by plan/scopes.
- Business/Enterprise plan restrictions may apply.

Community exporters that read local cache may be broken by encrypted cache changes. Do not rely on old `cache-v*.json` assumptions without verifying current file shape and support.

## Confirmed DJ Output Preferences

- Destination:

```text
H:\\My Drive\\Meeting_Notes
```

- Existing filename convention from screenshot:

```text
[Meeting Title] YYYY_MM_DD.txt
```

Examples observed used `.txt` files with date at the end, usually underscores inside the date; some historical variation used a space or underscore before the date. For new exports, prefer a space before the date unless DJ states otherwise:

```text
DJ <> Scott 1-1 Weekly 2026_08_07.txt
```

- Use the **meeting date**, not the export date.
- DJ wants the target end-state to be **fully automated/no touch**, not a copy/paste-assisted workflow.
- Current manual separator before transcript is:

```text
***
```

## Workflow Captured From PDF

The PDF `granola workflow.pdf` documented the current manual UI flow:

1. Granola home page: click the relevant meeting in the recent/home list.
2. Meeting detail page: click the top-right `...` menu.
3. Click `Copy notes` from the menu.
4. Paste notes into a blank text file.
5. Click/open the transcript/audio panel at the bottom of the meeting page.
6. Click the transcript panel's `Copy transcript` icon/button.
7. Paste transcript after `***`.
8. Save the `.txt` file.

Automation-relevant UI details:

- Meeting detail page shows title and a date pill (e.g. `Aug 7`) near the top.
- `Copy notes` lives under the top-right ellipsis menu beside the `Share` button.
- Transcript copy is a separate button/icon in the bottom transcript panel, with tooltip `Copy transcript`.
- The copied transcript includes metadata like `Meeting Title:`, `Date:`, `Meeting participants:`, then `Transcript:`.

## Recommended Future Workflow

1. Confirm whether the first no-touch version should export:
   - the currently open meeting,
   - the selected/highlighted meeting, or
   - the most recent completed meeting.
2. Prefer starting with **currently open meeting** for safety; it avoids exporting the wrong meeting from the home list.
3. Because free-plan/API paths may be blocked, use UI automation after validating the click/keyboard flow:
   - Power Automate Desktop recorder for fastest first no-touch prototype.
   - AutoHotkey v2 for a durable hotkey flow.
   - Python + pywinauto/UIAutomation if Granola exposes accessible selectors for `Copy notes` / `Copy transcript`.
4. Only offer assisted clipboard export as a fallback or intermediate prototype; DJ explicitly pushed toward no-touch automation.

## Style/Workflow Lesson

Do not jump from discovery output directly to creating a script with assumed defaults. The user explicitly corrected this. Explain the state of the investigation and ask for destination/format/automation choices before side effects. In particular, do not assume a default folder, default filename style, or assisted copy/paste workflow when the user's desired state is full automation.
