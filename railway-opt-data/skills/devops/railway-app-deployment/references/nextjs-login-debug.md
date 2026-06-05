# Railway + Next.js Production Login Debug Notes

Use these notes when a Railway-hosted Next.js app deploys but a login form/button appears inert.

## Durable lessons

- Railway CLI v5 token auth uses `RAILWAY_API_TOKEN`; normalize user-provided `RAILWAY_TOKEN` into it for backwards compatibility.
- `railway up --service <name> --detach` can deploy a specific service, but not every CLI v5 subcommand accepts `--service` (for example, `status --service` may fail). Verify by app-domain probes when CLI status flags differ by version.
- Direct API success does not prove browser-side login works. If clicking the button does nothing, verify the deployed client chunk contains the submit handler.
- Server-rendered HTML will not show React event handlers such as `onSubmit`; inspect JS chunks for strings like `/api/auth/login`, `window.location.assign`, or route pushes.
- If production is missing expected code, check `git status`, `git diff`, and `git diff --cached`: the fix may be staged locally but never committed/pushed/deployed.
- For Railway-hosted Prisma APIs that return blank 500s, inspect `railway logs` before patching. Prisma validation errors may be visible only in container logs.
- For Prisma `DateTime` fields, a date-only browser string like `2026-06-04` may validate at the API schema layer but fail in Prisma `update` data. Normalize once (for example `new Date(`${dateString}T00:00:00.000Z`)`) and remove the raw date string from ORM `create`/`update` objects.

## API/session verification probe

```bash
python3 - <<'PY'
import urllib.request, json, http.cookiejar
base='https://APP_DOMAIN'
cj=http.cookiejar.CookieJar()
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
body=json.dumps({'username':'USER','password':'PASSWORD'}).encode()
req=urllib.request.Request(base+'/api/auth/login', data=body, headers={'Content-Type':'application/json'}, method='POST')
resp=opener.open(req, timeout=30)
print('login status', resp.status, resp.read().decode())
print('session cookie set', any(c.name.endswith('session') for c in cj))
page=opener.open(base+'/', timeout=30).read().decode('utf-8','replace')
print('login form present', 'Private dashboard login' in page)
PY
```

## Deployed client handler probe

```bash
python3 - <<'PY'
import re, urllib.request
base='https://APP_DOMAIN'
html=urllib.request.urlopen(base+'/login', timeout=30).read().decode('utf-8','replace')
for src in re.findall(r'<script[^>]+src="([^"]+\.js)"', html):
    js=urllib.request.urlopen(base+src, timeout=30).read().decode('utf-8','replace')
    if '/api/auth/login' in js or 'window.location.assign' in js or 'router.push' in js:
        print('MATCH', src)
        print('has api/auth/login', '/api/auth/login' in js)
        print('has window.location.assign', 'window.location.assign' in js)
        print('has router.push', 'router.push' in js)
```
