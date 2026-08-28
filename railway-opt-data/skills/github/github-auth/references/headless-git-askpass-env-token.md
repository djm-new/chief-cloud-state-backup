# Headless Git push with env token and no credential store

Use this when `git push` fails in a headless environment with:

```text
fatal: could not read Username for 'https://github.com': No such device or address
```

and `gh` is unavailable plus no `~/.git-credentials` exists, but a GitHub token is already present in an env file such as `/opt/data/.env`.

## Safer one-shot push pattern

This avoids embedding the token in the remote URL or printing it in logs.

```bash
set -e
ASKPASS=$(mktemp)
cat > "$ASKPASS" <<'SH'
#!/bin/sh
case "$1" in
  *Username*) printf '%s\n' x-access-token ;;
  *Password*) awk -F= '/^GITHUB_TOKEN=/{print substr($0,index($0,"=")+1)}' /opt/data/.env ;;
  *) printf '\n' ;;
esac
SH
chmod 700 "$ASKPASS"
GIT_ASKPASS="$ASKPASS" GIT_TERMINAL_PROMPT=0 git push origin main
rm -f "$ASKPASS"
```

## Notes

- First verify the env file contains a token key name without printing the value.
- Keep the remote clean, e.g. `https://github.com/<owner>/<repo>.git`.
- Remove the temporary askpass script immediately after use.
- Prefer this over temporarily embedding `https://<token>@github.com/...` when logs or process listings are a concern.
