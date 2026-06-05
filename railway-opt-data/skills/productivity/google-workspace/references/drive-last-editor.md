# Drive last editor / last modifying user lookup

Use this when the user asks who last edited a Google Drive file or when the standard `drive get` wrapper returns `modifiedTime` but not `lastModifyingUser`.

## Pattern

1. Search Drive normally to identify the file and account:

```bash
/opt/data/scripts/google-account flow drive search 'BOD Jun 2026' --max 5
```

2. If `drive get FILE_ID` does not expose the required field, call Drive API directly with an explicit `fields` projection. In DJ's Railway Chief setup, account tokens live under `/opt/data/google-accounts/{personal|166-2nd|flow}/google_token.json`.

```bash
python3 - <<'EOF'
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

acct = 'flow'
file_id = 'FILE_ID_HERE'
token_path = f'/opt/data/google-accounts/{acct}/google_token.json'
creds_data = json.load(open(token_path))
creds = Credentials(
    token=creds_data.get('token'),
    refresh_token=creds_data.get('refresh_token'),
    token_uri=creds_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
    client_id=creds_data.get('client_id'),
    client_secret=creds_data.get('client_secret'),
)
svc = build('drive', 'v3', credentials=creds)
f = svc.files().get(
    fileId=file_id,
    fields='name,modifiedTime,lastModifyingUser(displayName,emailAddress,me,permissionId)'
).execute()
print(json.dumps(f, indent=2))
EOF
```

## Notes

- `modifiedTime` is UTC; convert to the user's local timezone in the answer when useful.
- `lastModifyingUser.me=true` means the authenticated account is the last editor; still report display name and email.
- Do not claim the editor from memory or from file owner; owner and last editor are different fields.
