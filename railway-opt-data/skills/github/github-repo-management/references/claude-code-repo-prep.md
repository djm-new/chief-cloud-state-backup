# Claude Code repo prep checklist

Use this when the user says they want to continue in Claude Code after Hermes work.

## Before handing off

- Confirm `git status --short --branch`
- Confirm the desired branch name
- Confirm `origin` points to the intended GitHub repo
- Confirm the commit(s) that should be visible on GitHub
- Confirm that any secrets/tokens remain untracked
- Confirm that the user wants the current state pushed now, not just committed locally

## If push fails

- Treat a username/password prompt from GitHub as an authentication problem, not a remote problem
- Verify whether the shell has `gh` auth or a `GITHUB_TOKEN`/`GH_TOKEN`
- If the environment is Railway/Chief, remember that production secrets may exist there even when a local shell does not

## Handoff note

Keep the repo in a state that another coding agent can open immediately:
- clean or explain dirty working tree
- clear commit message
- GitHub remote verified
- no secrets in the diff
