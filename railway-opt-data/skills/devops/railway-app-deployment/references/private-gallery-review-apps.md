# Private gallery/review apps on Railway

Use this reference for small secret-link apps where one or more people review cropped images/items and mark keep/discard/approve/reject.

## Durable patterns

- **Standalone product boundary:** create a dedicated GitHub repo and dedicated Railway service. Do not tuck a one-off review app under an unrelated deployed product just because it already has auth/hosting.
- **Secret-link route:** expose the working app at an unguessable user route such as `/books/<secret>`; keep `/health` only for deployment health.
- **Shared server-side decisions:** do not rely only on `localStorage` when multiple people need to coordinate. Save each item decision/category/rotation server-side, keyed by a stable hash/item id, and keep localStorage only as fallback/cache.
- **Persistent storage:** on Railway, attach a volume for JSON-backed MVP state (e.g. `/data/<app>/decisions.json`, `/data/<app>/activity.json`) if a database would be overkill. Verify the volume is `READY` before claiming persistence.
- **Activity tracking:** if the user wants to know who used the app, add lightweight server endpoints: heartbeat on page load/visibility/interval, action events on decisions, and a secret admin activity page. Track first seen, last seen, approximate active time, page loads, action counts, rough device label, user agent. Use separate user links or a first-run identity prompt if person-level attribution matters.
- **Completion contact sheet:** when review is done, add a dedicated contact sheet route that loads the shared decisions and image manifest, then renders scrollable/printable Keep and Discard sections. Include counts, titles, categories, and saved rotation. Add a link from the main review UI.

## Mobile-first UI defaults for item review

- Gallery: responsive 3x3/3x4-ish grid on mobile, big tappable cards, center tap opens detail view.
- Decisions: green check and red X corner buttons over the image; use fixed equal width/height and `border-radius: 50%` so buttons stay circular. If the user asks to restore original style, solid filled circles are preferred over transparent outlined ones.
- Detail view: title should be deciphered item title when possible, otherwise `Untitled`; subtitle should be human-readable such as `Category: Activity`, not debug hash/rotation strings.
- Detail decisions: check/X buttons should sit on the image like gallery controls; tapping the same decision again toggles it off; tapping the large center overlay clears the decision.
- Detail navigation: support swipe left/right across items and include visible chevrons or a “Swipe left/right” hint so the function is discoverable.
- Rotation: keep manual per-item rotation controls in detail view, but avoid putting rotate buttons on top of every gallery image unless explicitly requested.

## Verification checklist

1. Run local tests for UI markers and API routes.
2. Push to GitHub and trigger/poll the Railway deployment for the exact commit SHA.
3. Verify the real secret user route, not just `/health`.
4. Verify at least one image/manifest asset loads.
5. Verify server-side save/load by writing and reading a probe decision/action.
6. Verify the contact sheet route contains expected markers and decision counts from `/api/decisions`.
7. For visual crops/orientation, inspect produced contact sheets or real generated images before claiming the UI is usable.
