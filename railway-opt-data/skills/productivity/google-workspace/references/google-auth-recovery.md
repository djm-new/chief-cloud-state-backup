# Google auth recovery notes

Use this when Google Workspace commands fail before auth checks can complete.

## Recovery pattern

- If the Hermes venv has no `pip`, install the Google Workspace client deps with `uv` into the same interpreter:
  ```bash
  uv pip install --python /opt/hermes/.venv/bin/python \
    google-api-python-client google-auth-oauthlib google-auth-httplib2
  ```
- Re-run the auth check after the install:
  ```bash
  /opt/hermes/.venv/bin/python /opt/data/skills/productivity/google-workspace/scripts/setup.py --check
  ```
- To target a specific Google account, set `HERMES_HOME` to that account profile before running the setup or API wrapper:
  ```bash
  HERMES_HOME=/opt/data/google-accounts/flow \
    /opt/hermes/.venv/bin/python /opt/data/skills/productivity/google-workspace/scripts/setup.py --check
  ```

## What to verify

- `setup.py --check` should print `AUTHENTICATED` for the intended account.
- `google_api.py docs create` and other mutations should be run only after the intended account passes the check.
- If multiple accounts exist, check each one explicitly rather than assuming the default token path is authoritative.
