# Next.js / Railway PWA Bootstrap Pattern

Use this as a reusable pattern when a product-discovery session turns into a private Railway-hosted PWA build.

## Trigger

- User has approved product direction and says to move forward / keep going.
- Target is a private mobile-first web/PWA with desktop dashboard.
- External GitHub/Railway credentials may or may not be available yet.

## Workflow

1. Create a durable project directory and docs:
   - product spec
   - implementation plan
   - seed/config JSON if applicable
   - `PROJECT_STATUS.md` for continuity.
2. Initialize git immediately and commit small verified chunks.
3. Scaffold Next.js/TypeScript with:
   - `app/` routes
   - `components/`
   - `lib/`
   - `prisma/schema.prisma`
   - `tests/unit/`
   - `public/manifest.json`
   - `railway.json`
   - `.env.example`
4. Pick PostgreSQL + Prisma for relational health/workout/productivity data unless a stronger reason points elsewhere.
5. Implement deterministic domain logic first and test it before wiring UI:
   - calculations
   - progression rules
   - date/window logic
   - backup/export transforms.
6. Add a mobile-first static UI skeleton early so the user can react to flow/shape.
7. Add API scaffolds with validation and audit hooks before deep UI polish.
8. Verify after each chunk:
   ```bash
   npm run typecheck
   npm run test
   npm run build
   ```
9. Commit after each verified chunk.
10. If `gh`/`railway` are unauthenticated, install/check CLIs if useful, but do not stall: continue local implementation, record the auth blocker in `PROJECT_STATUS.md`, and summarize exactly what auth is needed.

## Pitfalls

- Do not treat unauthenticated GitHub/Railway as a reason to stop local work.
- Do not commit `.env`, local DB files, `node_modules/`, `.next/`, or `*.tsbuildinfo`.
- Do not hard-code product-specific coaching/business logic into the app if the app should remain a neutral tracker/importer.
- If a file-write linter fires before dependencies/config are fully installed, switch to command-level verification rather than looping on the write tool.
- **The per-file `write_file` linter produces noisy false-positive errors from `node_modules` type declarations** (missing `VAR_MODULE_GLOBAL_ERROR`, React default-import flags, etc). These are pre-existing and do not indicate new errors. Treat them as noise — rely on `npm run typecheck` (full `tsc --noEmit`) as the authoritative type check, not the per-file linter.
- **`as const` on empty array fallbacks breaks type inference.** `[[], [], [], null] as const` makes the inner arrays `readonly []`, which Prisma's mutable arrays won't accept. Drop `as const` on multi-value fallback tuples.
- **Test fixture assumptions are the first cause of spurious RED→fix-test loops.** Read JSON seed files before writing expectations. Compute aggregate math explicitly before asserting it. See `test-driven-development` skill anti-patterns.
- **Dashboard calorie balance: only include days that have actual data.** A day with no meals and no calorie log entry should not contribute a full TDEE deficit to the 7-day balance — only include days where `caloriesIn > 0` or `activeCalories/restingCalories` are non-null.

## DJ execution style

DJ's explicit preference: do not stop mid-project asking "shall I continue?" or "what's next?" — just keep going until the feature is done, verified, and committed, or until an external blocker (auth, credentials, destructive action) forces a genuine pause. See the `DJ active-project mode` section in the main `writing-plans` SKILL.md.

## Good status file contents

- Current path and branch
- Completed features
- Latest verification commands and results
- Local commits
- External blockers
- Next implementation work
