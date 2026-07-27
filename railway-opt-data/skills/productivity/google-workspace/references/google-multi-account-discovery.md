# Google multi-account discovery

When Drive/Docs items seem missing, assume the host may have multiple connected Google Workspace accounts and verify the account before concluding the file is inaccessible.

## Discovery pattern
- Enumerate the available local token profiles under `.../google-accounts/` when present.
- For each candidate profile, refresh the token and call Drive `about` to identify the user email/display name.
- Prefer the account that matches the source context:
  - Flow workspace docs → Flow account
  - Personal docs → personal account
  - Other workspace-sourced docs → the matching workspace token

## Verification
- If a folder path exists in one account but appears empty in another, check the signed-in account shown in the UI before assuming upload failure.
- When uploading or reading a doc, prefer the account that can already open the source document or sees the expected parent folder.
- If multiple profiles are valid, state which account was used for the operation.

## Pitfall
- Do not stop at the first authenticated token path. A missing default token does not mean the machine has no usable Google access.
