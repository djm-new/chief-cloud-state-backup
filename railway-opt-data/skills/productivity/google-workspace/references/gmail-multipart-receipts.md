# Gmail multipart receipts and blank bodies

Use this when `google_api.py gmail get MESSAGE_ID` returns `body: ""` for a billing receipt or other rich/multipart email.

## Pattern

1. Search normally with the wrapper, targeting the intended account explicitly:

```bash
HERMES_HOME=/opt/data/google-accounts/personal \
  /opt/data/google-accounts/.venv/bin/python \
  /opt/data/skills/productivity/google-workspace/scripts/google_api.py \
  gmail search '(railway OR stripe OR invoice OR receipt) newer_than:180d' --max 30
```

2. If `gmail get` is empty, read with Gmail API `format='full'` and walk MIME parts:

```python
import base64
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

home = Path('/opt/data/google-accounts/personal')
creds = Credentials.from_authorized_user_file(str(home / 'google_token.json'))
svc = build('gmail', 'v1', credentials=creds)
msg = svc.users().messages().get(userId='me', id=MESSAGE_ID, format='full').execute()

def decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))

def walk(part, depth=0):
    mime = part.get('mimeType')
    body = part.get('body', {})
    data = body.get('data')
    if data and mime in ('text/plain', 'text/html'):
        print(decode(data).decode('utf-8', 'replace'))
    for child in part.get('parts', []) or []:
        walk(child, depth + 1)

walk(msg['payload'])
```

3. For receipts, inspect `text/plain` first; it often contains the exact line items even when HTML is large. Attachments usually appear as `application/pdf` parts with `attachmentId` if the user needs the invoice PDF later.

## Notes

- Stripe receipts can come from senders like `invoice+statements+...@stripe.com` with `Reply-To: billing@...`; searching only `from:railway.com` can miss them.
- Keep Google policy: reading/summarizing is OK; never send/reply/forward without explicit user approval.
