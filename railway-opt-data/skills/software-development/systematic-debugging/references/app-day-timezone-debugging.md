# App-Day / Timezone Debugging for Date-Driven Web Apps

Use this when a production app shows the wrong day, logs data to tomorrow/yesterday, or dashboard totals do not match the user's calendar day.

## Symptom pattern

- User says the app shows the next date while it is still the prior evening locally.
- Meals/daily logs appear under the wrong day after UTC midnight.
- Server-rendered dashboards and client date inputs disagree.
- Date picker defaults use `new Date().toISOString().slice(0, 10)`.

## Root cause pattern

Server runtimes often run in UTC. If the product's day is tied to a user's timezone, UTC date keys are wrong during the offset window. For US Eastern, `2026-06-05T00:30:00Z` is still `2026-06-04 20:30 EDT`.

## Debugging steps

1. Verify server time and target app timezone:

```bash
date
TZ=America/New_York date
```

2. Search for UTC date-key helpers:

```bash
rg "toISOString\(\)\.slice\(0, 10\)|Date\.UTC|getUTCFullYear|startOfUtcDay|new Date\(\)" .
```

3. Identify every place that defines an app day:

- dashboard selected day
- default date inputs
- meal `date` field
- daily-log `date` field
- workout session `date` field
- goal lookup windows
- rolling metrics windows
- history pages and API query params

4. Centralize date-key conversion in one helper, e.g.:

```ts
export const APP_TIME_ZONE = 'America/New_York';

export function appDateKey(date: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: APP_TIME_ZONE,
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(date);
  const byType = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${byType.year}-${byType.month}-${byType.day}`;
}

export function appDateKeyToStoredDate(dateKey: string): Date {
  return new Date(`${dateKey}T00:00:00.000Z`);
}

export function storedDateForAppDay(date: Date = new Date()): Date {
  return appDateKeyToStoredDate(appDateKey(date));
}
```

5. Store app-day dates canonically as midnight UTC for the date key, but derive the key from the app timezone first.

6. Add a regression test for the offset window:

```ts
expect(appDateKey(new Date('2026-06-05T00:30:00.000Z'))).toBe('2026-06-04');
expect(storedDateForAppDay(new Date('2026-06-05T00:30:00.000Z')).toISOString()).toBe('2026-06-04T00:00:00.000Z');
```

## Pitfalls

- Do not patch only the visible label. All aggregation queries and write paths must use the same app-day helper.
- Do not use `toISOString().slice(0, 10)` for user-facing app-day defaults unless the app's day is explicitly UTC.
- Do not mix client local timezone, server UTC, and product timezone ad hoc. Pick the product timezone and centralize it.
- For date-driven history pages, explicit `?date=YYYY-MM-DD` params should be treated as app-date keys and converted to canonical stored dates.
