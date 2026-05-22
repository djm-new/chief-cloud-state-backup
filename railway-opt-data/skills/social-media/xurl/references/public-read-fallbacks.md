# Public Read Fallbacks for X Posts

Use this for **read-only** requests like "can you read this thread?" when authenticated `xurl` is unavailable or not necessary. These are best-effort public fallbacks; they do not replace authenticated API access for complete timelines, protected posts, writes, or reliable thread reconstruction.

## Focal post via oEmbed

```bash
python3 - <<'PY'
from urllib.request import Request, urlopen
from urllib.parse import quote
import json, html, re
status_url = 'https://x.com/wolfejosh/status/2057228078963920899'
url = 'https://publish.twitter.com/oembed?omit_script=true&url=' + quote(status_url, safe='')
body = urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=20).read().decode()
obj = json.loads(body)
text = re.sub('<br\s*/?>', '\n', obj['html'])
text = re.sub('<[^>]+>', '', text)
print(html.unescape(text))
PY
```

This usually returns the tweet text embedded in the HTML blockquote. It may not include thread replies.

## Focal post JSON via FxTwitter/VxTwitter

```bash
curl -L -s -A 'Mozilla/5.0' \
  'https://api.fxtwitter.com/wolfejosh/status/2057228078963920899' | python3 -m json.tool

curl -L -s -A 'Mozilla/5.0' \
  'https://api.vxtwitter.com/wolfejosh/status/2057228078963920899' | python3 -m json.tool
```

Useful fields:

- `tweet.text` / `text` — post body without labels or HTML.
- `tweet.author` / `user_*` — author metadata.
- `tweet.media.photos[].url`, `mediaURLs`, `media_extended` — media URLs for download/OCR/vision.
- `replies`, `conversationID` — hints that a continuation exists, not a guarantee the mirror returned it.

## Media extraction + OCR

When the post is an image/card, download media and run OCR or vision:

```bash
python3 - <<'PY'
from urllib.request import Request, urlopen
url = 'https://pbs.twimg.com/media/HIy-CQwWQAAQG6t.jpg?format=jpg&name=orig'
data = urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=30).read()
open('/tmp/x-post-media.jpg', 'wb').write(data)
print(len(data))
PY

# If tesseract/ImageMagick are available:
magick /tmp/x-post-media.jpg -resize 250% -colorspace Gray -sharpen 0x1 -contrast-stretch 1%x1% /tmp/x-post-media-ocr.png
tesseract /tmp/x-post-media-ocr.png stdout --psm 6
```

## Reporting limitations

Be precise about coverage:

- "I can read the focal post and attached image; I cannot confirm the full thread from public mirrors." 
- "Metadata says there are N replies, but the fallback source only returned the starting post."
- Do not turn a setup/auth limitation into a durable claim that X/Twitter cannot be read. Authenticated `xurl` may work when configured.
