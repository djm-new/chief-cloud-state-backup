# HealthOS Daily Ledger UX Notes

Use these notes when planning or implementing HealthOS dashboard, meals, daily metrics, and history flows for DJ.

## Core product model

HealthOS should behave like a **daily ledger**, not a collection of disconnected quick-entry cards.

DJ's workflow:

1. Log meals and activity during the day.
2. After the day is over, flip back to yesterday.
3. Confirm all meals/activity for that day.
4. Enter/finalize calories out, weight, sleep, and other daily metrics.
5. Review history across days.

The UI should make date navigation and day-level review first-class.

## Required interaction patterns

- Dashboard and Meals pages should be date-driven, e.g. `?date=YYYY-MM-DD`.
- Provide obvious day navigation: previous day, Today, next day, date picker, and explicit Go/submit for mobile reliability.
- Use the app timezone (`America/New_York`) for the app day, not UTC server day.
- The selected date should drive all visible data: meal totals, meal list, daily metrics, calories out, sleep, weight, and workouts.
- Users should be able to inspect and edit yesterday's data without changing today's data.

## Meals UX

Meals should be shown as grouped editable tables, not loose cards:

- Groups: breakfast, lunch, dinner, snack.
- Columns: meal description, calories, protein, carbs, fat, meal type/category, actions.
- Descriptions should be normal editable text fields, e.g. `SG Harvest Bowl`.
- Macros should be directly editable inline.
- Meal type/category should be editable inline.
- Include Save/Delete per row.
- Show subtotal per meal group and daily total across all groups.

## Mobile pitfalls

- Avoid sticky/toggle pill selectors for meal type if they can get stuck or feel unreliable on iPhone.
- Prefer a normal `<select>` for meal type on mobile-sensitive flows.
- Do **not** rely on a horizontally scrollable data table as the primary mobile editing UI for logged meals. On ~390px iPhone screens, table auto-layout can shrink macro inputs into tiny boxes where values are clipped even though the table technically scrolls.
- Use responsive dual rendering for editable meal history: stacked editable cards on mobile, table layout only above a tablet/desktop breakpoint. Mobile cards should show description full-width, macros in a 2-column grid, type dropdown, and Save/Delete buttons with 16px input text to avoid iOS zoom/clipping.
- Wide meal tables can remain available on desktop/tablet, but keep date navigation and daily totals readable without horizontal scroll.
- Date picker changes should have an explicit Go button; do not rely solely on browser-specific date input behavior.

## Daily metrics UX

Daily metrics are often finalized the next day. A selected-day metrics card should allow editing:

- active calories
- resting calories
- calories-out total display
- weight
- steps
- sleep as hours + minutes, never decimal hours

Saving daily metrics should refresh the server-rendered cards for the selected date.

## History expectation

A generic history/meal page should show each day's history, not only today's list. At minimum, support date navigation on `/meals`; ideally add a multi-day table/summary later.

## Pitfalls observed

- Server-rendered metric cards must refresh after client-side meal or daily-log saves (`router.refresh()` in Next App Router).
- Avoid UTC-derived `new Date().toISOString().slice(0, 10)` for app-day defaults; after 8pm ET it shows tomorrow.
- Do not optimize for login/settings polish before the core daily review workflow; DJ explicitly called login/password the least useful part.
