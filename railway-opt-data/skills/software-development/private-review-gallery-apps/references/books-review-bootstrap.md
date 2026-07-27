# Books Review Bootstrap Notes

This session confirmed the fastest way to start a fresh books-sorting app is to clone the proven book-sorter MVP structure into a new repo/service, then rename the visible routes and labels.

## What to carry over

- FastAPI server with:
  - review page route
  - contact-sheet route
  - decisions API
  - activity heartbeat/action API
  - admin activity page
- Mobile-first gallery + detail modal UX
- Shared server-side decisions backed by persistent volume
- Intro banner/splash before gallery loads
- Final keep/discard contact sheet for physical sorting
- Sample crop manifest and sample assets for immediate demoability

## Books-specific adjustments

- Rename the visible title/branding from the generic sorter label to a books-focused label.
- Keep the secret-link structure, but use a new secret path for the new app.
- Keep the contact-sheet route on the same pattern so the sorting workflow stays fast.
- Use the new books photo as the first scoping reference: it is a good fit for the same gallery/contact-sheet workflow because the items are well separated on a dark wood background.

## Bootstrap checklist

1. Copy the proven app scaffold into a fresh project directory.
2. Rename copy text, route labels, and page titles.
3. Reuse the shared server-side decisions and activity tracking pattern.
4. Run tests locally before touching deployment wiring.
5. Verify the real review route and the contact-sheet route after deploy.
