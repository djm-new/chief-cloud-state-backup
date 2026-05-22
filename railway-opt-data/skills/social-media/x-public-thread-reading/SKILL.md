---
name: x-public-thread-reading
description: "Best-effort reading of public X/Twitter posts when xurl auth is unavailable."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [twitter, x, public, thread-reading, ocr]
---

# X Public Thread Reading Fallback

Use this when the user asks to read an X/Twitter URL and official `xurl` auth is missing or failing.

## Workflow

1. Prefer the official path if authenticated:
   ```bash
   xurl auth status
   xurl read <tweet-id-or-url>
   ```
   If this returns 401/Unauthorized or says no apps are registered, continue with the public fallback.

2. Run the best-effort reader script:
   ```bash
   python3 /opt/data/scripts/read_x_thread.py 'https://x.com/user/status/123'
   ```

3. Inspect the JSON output:
   - `tweets[].texts`: post text from fx/vx/oEmbed/X embedded state
   - `tweets[].media`: media URLs
   - `tweets[].ocr`: OCR text from attached images
   - `notes`: source successes/failures

4. Be explicit about limitations. Public endpoints often expose only the focal post, not a full thread/conversation. For reliable full thread reading, the user must configure X API credentials for `xurl`.

## Setup already done on this environment

- `/usr/local/bin/xurl` is installed.
- `/opt/data/scripts/read_x_thread.py` exists and is executable.
- `tesseract-ocr` is installed for image OCR.

## User-side auth required for reliable reads

The agent must not handle secrets. Ask the user to run these manually if they want reliable official X API reads:

```bash
xurl auth apps add <app-name> --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
xurl auth oauth2 --app <app-name> YOUR_X_USERNAME
xurl auth default <app-name> YOUR_X_USERNAME
xurl auth status
xurl read <tweet-id-or-url>
```

The X app redirect URI should be `http://localhost:8080/callback`.

## Pitfalls

- Do not read or print `~/.xurl`; it contains secrets.
- Do not use `--verbose` with `xurl`; it may expose auth headers.
- Public mirrors may be stale, rate-limited, or incomplete.
- X logged-out pages may contain only the focal post in embedded state.
