# Railway shell vs repo checkout

Use this when a user wants to run git commands from Railway and the exact shell location matters.

## Core distinction

- **Railway service console / shell**: a terminal attached to the running app container.
- **Repo checkout shell**: a terminal on the machine or volume where the project files actually live.

Do not assume the service console contains the repository checkout.

## Sanity check before giving push instructions

Run a quick probe in the user-facing shell:

```bash
pwd
ls
ls /opt/data/projects/healthos 2>/dev/null || true
git rev-parse --show-toplevel 2>/dev/null || true
git remote -v 2>/dev/null || true
```

Interpretation:

- If the repo path is missing and `git rev-parse` fails, the shell is **not** attached to the checkout you want.
- If the prompt is in the app container but the repo lives elsewhere, direct the user to the correct shell instead of continuing to guess commands.

## Communication pattern

When the user asks “where do I run this?”, answer with:

1. the exact place to open
2. the exact commands to run there
3. the one check that confirms they are in the right place

Prefer a single direct path over presenting menus of options.

## Verification checklist

- shell location identified
- repo checkout confirmed
- auth source for GitHub identified
- push command run from the shell that has both repo and auth
