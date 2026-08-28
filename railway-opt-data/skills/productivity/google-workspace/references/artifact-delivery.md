# Artifact delivery for user-facing files

Use this pattern when the user asks for a file they need to open or download later.

## Preferred flow

1. Create the artifact locally only as an intermediate step if needed.
   - Treat `/opt/...`, Railway volumes, and VM paths as disposable cache, not durable user-facing storage.
   - If the file is part of a source repo/corpus, push it to GitHub; if it is a user-facing deliverable, upload it to Drive.
2. Upload the final file to the live temp folder in the user's personal Drive:
   - `My Drive > Chief_of_Staff > Projects > Hermes_temp_folder`
3. Re-read the uploaded file metadata and confirm:
   - file name
   - parent folder ID
   - webViewLink
4. Reply with the Drive link, not a local Railway/VM path.

## PDF-specific note

If a PDF must be produced, prefer a standards-compliant producer or export path
that can be re-opened by Adobe/Drive. If a file cannot be opened cleanly, rebuild
it and verify the uploaded result before handing it off.
