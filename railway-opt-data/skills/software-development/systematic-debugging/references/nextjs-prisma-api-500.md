# Next.js + Prisma API 500 Debug Notes

Use this reference when a browser form shows a generic failure message but a Railway/Next.js API route returns HTTP 500.

## Reproduction pattern

1. Log in with a real session using a cookie jar.
2. POST the smallest payload that matches the UI action.
3. Capture status and response body.
4. Pull server logs for the exact ORM/runtime error.

```bash
python3 - <<'PY'
import urllib.request, urllib.error, json, http.cookiejar
base='https://APP_DOMAIN'
cj=http.cookiejar.CookieJar()
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

login=json.dumps({'username':'USER','password':'PASSWORD'}).encode()
opener.open(urllib.request.Request(base+'/api/auth/login', data=login, headers={'Content-Type':'application/json'}, method='POST'), timeout=30).read()

payload={'date':'2026-06-04','weightLb':None,'activeCalories':None,'restingCalories':None,'steps':None,'sleepMinutes':408}
req=urllib.request.Request(base+'/api/daily-log', data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'}, method='POST')
try:
    r=opener.open(req, timeout=30)
    print('status', r.status, r.read().decode())
except urllib.error.HTTPError as e:
    print('status', e.code, e.read().decode('utf-8','replace'))
PY
```

## Root-cause pattern observed

Prisma `DateTime` fields reject date-only strings such as `"2026-06-04"` in writes. A route can appear correct if it normalizes the date for `create`, but still fail when the `update` half of an `upsert` receives raw parsed client data:

```ts
// Broken: parsed.data still includes date: "YYYY-MM-DD"
await prisma.dailyHealthLog.upsert({
  where: { userId_date: { userId, date } },
  update: parsed.data,
  create: { ...parsed.data, userId, date },
});
```

Fix by separating client-only/raw fields from ORM data:

```ts
const { date: dateString, ...logData } = parsed.data;
const date = new Date(`${dateString}T00:00:00.000Z`);

await prisma.dailyHealthLog.upsert({
  where: { userId_date: { userId, date } },
  update: logData,
  create: { ...logData, userId, date },
});
```

## Verification

- Re-run the exact minimal POST and expect HTTP 200.
- Fetch the dashboard or a read endpoint and verify the saved value appears.
- If deploying on Railway, direct app-domain probes may be more reliable than CLI status flags for confirming the new build is active.
