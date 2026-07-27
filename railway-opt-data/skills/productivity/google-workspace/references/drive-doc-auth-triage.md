# Drive/Docs auth triage

Use this when a Google Doc or Drive file is known to exist but the first access attempt lands on a sign-in wall or returns 403.

## Fast triage

1. Check for multiple Hermes Google profiles/tokens on disk.
2. For each candidate token, refresh it and probe the Docs API directly with the document ID.
3. Prefer the first account that can read the document without prompting for browser auth.

## Minimal probe pattern

- Refresh access token via the token's `client_id`, `client_secret`, `refresh_token`, and `token_uri`.
- Call `https://docs.googleapis.com/v1/documents/<DOC_ID>` with `Authorization: Bearer <access_token>`.
- If Docs API succeeds, extract text from `body.content` paragraphs and tables.

## Practical notes

- A Google Docs URL may look accessible in the browser but still be easier to read through the Docs API.
- If one token 403s, try the next profile token before concluding the doc is inaccessible.
- If the file is a shared Drive doc, the exact account that can read it may not be the one currently used by the wrapper skill.

## What to return to the user

- Doc title
- The specific account/profile that worked, if relevant
- A concise text extract or structured summary of the document contents
- The original sign-in wall clearly called out if no token can access it