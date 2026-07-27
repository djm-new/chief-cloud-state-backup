# Drive temporary-folder convention

When DJ says to put a temporary file somewhere, use the personal Drive path:

- `My Drive > Chief_of_Staff > Projects > Hermes_temp_folder`

## Reliable upload flow

1. Search the personal Drive for the live folder by name:
   - `name = 'Hermes_temp_folder' and trashed = false`
2. Do not assume the folder ID from a prior session is still valid.
3. Verify the file is absent in that folder before uploading if you want to avoid duplicates.
4. Upload the file to the resolved folder ID.
5. Re-read the uploaded file metadata and confirm:
   - file name
   - parent folder ID
   - webViewLink

## Why this matters

DJ corrected the folder path after an upload landed in the wrong account/folder. The key lesson is to resolve the live folder in the target account first, then upload and verify.

## Example metadata check

After upload, read the file with Drive fields like:

- `id`
- `name`
- `parents`
- `webViewLink`
