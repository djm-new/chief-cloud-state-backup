# Attachment intake for Slack/Drive

Use this when the user wants you to read a document or attachment from Slack or Google Drive.

## Preferred input order
1. Uploaded file in chat
2. Google Drive share link or file ID
3. Slack message link or thread link
4. Plain-text description only as a last resort

## Fast triage
- If the user only names a sender/topic, search local briefing archives, Slack/email context, or session notes for identifying hints (sender, role, project, likely title, exact URL).
- If the document was shared in Slack/email, recover the surrounding thread/message first so you can confirm the intended file before attempting OCR or web extraction.
- If multiple candidate files exist, ask the user to choose the exact one before summarizing.
- Once a direct link or file is available, read the document first and then summarize; don’t guess from the topic alone.
- If the source hint suggests a specific workspace/account (for example a Flow.life doc), run the multi-account sweep first instead of assuming the default Google token is the right identity.
- If the doc is behind a Google sign-in wall, say so explicitly and return the exact source link plus the nearest contextual message.

## Output discipline
- Report whether you found the exact document or only a likely match.
- If the content is sensitive or ambiguous, quote the title/source line before summarizing.