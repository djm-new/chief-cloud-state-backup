# Railway Auth Verification

Use this when you have a Railway token but need to confirm it is valid before attempting deploy/link operations.

## Quick checks

### CLI check

```bash
export RAILWAY_API_TOKEN='<token>'
export RAILWAY_TOKEN="$RAILWAY_API_TOKEN"
railway whoami
```

If `railway whoami` fails, stop and fix auth before investigating repo linkage or deploy state.

### Direct GraphQL read check

Railway GraphQL endpoint:

- `https://backboard.railway.com/graphql/v2`

Headers:

- `Authorization: Bearer <token>`
- `Content-Type: application/json`
- `User-Agent: Mozilla/5.0`

Minimal probe:

```bash
curl -sS \
  -H "Authorization: Bearer $RAILWAY_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Mozilla/5.0' \
  --data '{"query":"query { __typename }"}' \
  https://backboard.railway.com/graphql/v2
```

A successful response should return `{"data":{"__typename":"Query"}}`.

## Why this matters

- `railway whoami` is the fastest first gate.
- A direct GraphQL read confirms the token is accepted by the Railway API itself.
- This is useful when a CLI identity check is ambiguous but the token may still work for API reads.
