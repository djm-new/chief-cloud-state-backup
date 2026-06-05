# Next.js App Router: Client Mutation Does Not Update Server-Rendered Cards

Use when a Next.js App Router page has server-rendered metrics/cards and a client component saves data successfully, but visible dashboard values do not change until a manual refresh.

## Symptom

- Client form shows success (for example `Logged ...` or `Saved ...`).
- API write succeeds and DB/API totals reflect the new value.
- Top cards/metrics on the same page stay stale.
- A full browser refresh or fresh server fetch shows the updated values.

## Root cause pattern

In App Router, server components render their data on the server. A client component mutation (`fetch('/api/...', { method: 'POST' })`) does not automatically re-fetch the parent server component tree. The client must trigger a route refresh after a successful mutation.

## Investigation steps

1. Reproduce API write directly with an authenticated session.
2. Read the page: identify whether cards/metrics are computed in a server component.
3. Read the client form component: check whether it calls `router.refresh()` after success.
4. Verify date/window logic separately so you do not mistake a stale render for a date mismatch.
5. Inspect deployed JS assets if production behavior differs from local source.

## Fix pattern

In the client component:

```tsx
'use client';

import { useRouter } from 'next/navigation';
import { useState, useTransition } from 'react';

export function MutationForm() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function submit() {
    startTransition(async () => {
      const response = await fetch('/api/example', { method: 'POST' });
      if (!response.ok) return;
      router.refresh();
    });
  }
}
```

## Verification

- Confirm production JS chunk contains the new refresh-capable client bundle.
- Create a temporary test record, compare totals before/after through an API endpoint or server HTML, then delete/soft-delete the record if possible.
- Do not leave test meals/logs/workouts in the user’s data.