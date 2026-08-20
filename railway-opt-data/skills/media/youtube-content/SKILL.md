---
name: youtube-content
description: "YouTube transcripts to summaries, threads, blogs."
platforms: [linux, macos, windows]
---

# YouTube Content Tool

## When to use

Use when the user shares a YouTube URL or video link, asks to summarize a video, requests a transcript, or wants to extract and reformat content from any YouTube video. Transforms transcripts into structured content (chapters, summaries, threads, blog posts).

Extract transcripts from YouTube videos and convert them into useful formats.

## Setup

```bash
pip install youtube-transcript-api
```

## Helper Script

`SKILL_DIR` is the directory containing this SKILL.md file. The script accepts any standard YouTube URL format, short links (youtu.be), shorts, embeds, live links, or a raw 11-character video ID.

```bash
# JSON output with metadata
python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# Plain text (good for piping into further processing)
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only

# Timestamped plain text for deliverable transcript files
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps --text-only

# Timestamped JSON (metadata + full_text + timestamped_text field)
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps

# Specific language with fallback chain
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --language tr,en
```

If the active Python environment has no `pip` (common in stripped Hermes installs), install the dependency with uv instead:

```bash
uv pip install --python /opt/hermes/.venv/bin/python youtube-transcript-api
```

## Output Formats

After fetching the transcript, format it based on what the user asks for:

- **Chapters**: Group by topic shifts, output timestamped chapter list
- **Summary**: Concise 5-10 sentence overview of the entire video
- **Chapter summaries**: Chapters with a short paragraph summary for each
- **Thread**: Twitter/X thread format — numbered posts, each under 280 chars
- **Blog post**: Full article with title, sections, and key takeaways
- **Quotes**: Notable quotes with timestamps

### Example — Chapters Output

```
00:00 Introduction — host opens with the problem statement
03:45 Background — prior work and why existing solutions fall short
12:20 Core method — walkthrough of the proposed approach
24:10 Results — benchmark comparisons and key takeaways
31:55 Q&A — audience questions on scalability and next steps
```

## Workflow

1. **Identify sources**: if the user asks for “new/recent” videos without URLs, web-search for the likely title/guest/show, prefer official YouTube/podcast pages, and capture title, show, date, URL, and video ID.
2. **Fetch** the transcript using the helper script with `--timestamps --text-only` for clean transcript deliverables. Use JSON only when you need metadata programmatically.
3. **Validate**: confirm the output is non-empty and in the expected language. If empty, retry without `--language` to get any available transcript. If still empty, tell the user the video likely has transcripts disabled.
4. **Package multi-video requests**: create one timestamped `.txt` per video plus a combined `.txt`; zip them together for delivery. Include title, show/channel, date when known, source URL, video ID, and segment count at the top of each file.
5. **Chunk if needed**: if a transcript exceeds ~50K characters and the user asked for a summary/analysis, split into overlapping chunks (~40K with 2K overlap) and summarize each chunk before merging. Do not summarize when the user asked for raw transcripts unless they also request analysis.
6. **Transform** into the requested output format. If the user did not specify a format, default to the raw transcript for “transcript” requests and a summary for “summarize” requests.
7. **Verify**: check file sizes/non-empty content and verify ZIP integrity (for example, Python `zipfile.ZipFile(path).testzip() is None`) before presenting. Deliver the artifact with `MEDIA:/absolute/path`.

## Error Handling

- **Transcript disabled**: tell the user; suggest they check if subtitles are available on the video page.
- **Private/unavailable video**: relay the error and ask the user to verify the URL.
- **No matching language**: retry without `--language` to fetch any available transcript, then note the actual language to the user.
- **Dependency missing**: run `pip install youtube-transcript-api` and retry.
