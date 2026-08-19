# Artifact delivery checklist

Use when DJ asks for a chat transcript, PDF, attachment, or other exported deliverable from a conversation.

## Rules

- Produce the *requested artifact type* exactly. Do not substitute a transcript file when the user asked for a PDF, and do not answer with a summary when they asked for the artifact.
- Include the latest user message unless the user explicitly excludes it.
- If the user requests "our whole chat today" or similar, interpret that as the full conversation up to and including the current turn.
- For Drive-bound deliverables, upload to the exact folder the user named and return the Drive link.
- Verify the file is valid/openable before claiming success.
- If the first artifact is malformed or the wrong type, replace it with a corrected version rather than piling on a second confusing deliverable.

## Practical verification

- PDFs: check they open locally or with a parser, and confirm the file size is non-zero.
- Text exports: confirm the file contains the requested range of messages.
- Drive uploads: confirm the parent folder ID and webViewLink in the upload response.

## Common failure modes

- Making a text transcript when the user asked for a PDF.
- Omitting the latest message from the export.
- Reporting a local path as the deliverable instead of the uploaded file link.
- Sending multiple competing artifacts without clearly replacing the bad one.
