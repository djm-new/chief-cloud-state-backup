# Secret-link Railway app verification

Use this when the app is meant to be opened via a private/unguessable URL instead of a public homepage.

## Pattern
- Expose the actual app at a hard-to-guess path, e.g. `/books/<secret>`.
- Keep a simple public health route only for deployment checks.
- Verify the *real* user route after deploy, not only `/api/health`.

## Post-deploy checks
1. Fetch the live app route and confirm it returns HTTP 200.
2. Confirm the page contains a unique app marker, such as the app title or a known UI string.
3. Fetch at least one linked asset or sub-route and confirm the MIME type or payload is correct.
4. If the app is framed by a wrapper page, verify the wrapper points to the embedded app source and the source contains the expected title/marker.

## Useful markers
- app title or hero text
- iframe `src` for wrapper pages
- asset `Content-Type` such as `image/jpeg` or `text/html`
- health endpoint JSON like `{"ok":true}`
