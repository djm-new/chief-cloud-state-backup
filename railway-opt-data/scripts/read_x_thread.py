#!/usr/bin/env python3
"""Best-effort X/Twitter public post/thread reader for Hermes.

Usage:
  python3 /opt/data/scripts/read_x_thread.py 'https://x.com/user/status/123'

What it does:
- Uses public mirror APIs (fx/vx Twitter) for tweet metadata/text/media.
- Uses Twitter oEmbed as a fallback.
- Fetches the X logged-out page and extracts embedded tweet entities.
- Downloads attached images and OCRs them with tesseract when available.
- If xurl is authenticated, also tries `xurl read` for the official API path.

Limitations:
- Full conversation/thread expansion is not reliable without authenticated X API access.
- Public X pages often expose only the focal post in embedded state.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def fetch(url: str, timeout: int = 20, binary: bool = False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def extract_status_id(s: str) -> str:
    m = re.search(r"status/(\d+)", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d{5,}", s):
        return s
    raise SystemExit(f"Could not find status id in: {s}")


def extract_handle(s: str) -> str | None:
    m = re.search(r"(?:x|twitter)\.com/([^/?#]+)/status/\d+", s)
    return m.group(1) if m else None


def add_tweet(tweets: dict, source: str, tid: str, author: str | None, text: str, media=None, raw=None):
    if not text and not media:
        return
    cur = tweets.setdefault(tid, {"id": tid, "author": author, "texts": [], "media": [], "sources": [], "raw": []})
    if author and not cur.get("author"):
        cur["author"] = author
    if text and text not in cur["texts"]:
        cur["texts"].append(text)
    for u in media or []:
        if u and u not in cur["media"]:
            cur["media"].append(u)
    if source not in cur["sources"]:
        cur["sources"].append(source)
    if raw is not None:
        cur["raw"].append(raw)


def strip_oembed_html(h: str) -> str:
    h = re.sub(r"<br\s*/?>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    return html.unescape(h).strip()


def try_xurl(tid: str, tweets: dict):
    if not shutil.which("xurl"):
        return "xurl not installed"
    try:
        p = subprocess.run(["xurl", "read", tid], text=True, capture_output=True, timeout=25)
    except Exception as e:
        return f"xurl failed to run: {e}"
    if p.returncode != 0:
        return "xurl not authenticated or API denied: " + (p.stderr or p.stdout)[:300].replace("\n", " ")
    try:
        data = json.loads(p.stdout)
        obj = data.get("data", data)
        text = obj.get("text") or obj.get("full_text") or ""
        add_tweet(tweets, "xurl", obj.get("id", tid), None, text, raw=data)
        return "xurl ok"
    except Exception as e:
        return f"xurl returned non-parseable output: {e}"


def try_fx_vx(handle: str | None, tid: str, tweets: dict):
    urls = []
    if handle:
        urls += [
            f"https://api.fxtwitter.com/{handle}/status/{tid}",
            f"https://api.vxtwitter.com/{handle}/status/{tid}",
        ]
    urls += [f"https://api.fxtwitter.com/status/{tid}"]
    notes = []
    for u in urls:
        try:
            data = json.loads(fetch(u, timeout=20))
        except Exception as e:
            notes.append(f"{u}: {type(e).__name__}: {e}")
            continue
        # fxtwitter shape
        if "tweet" in data:
            tw = data["tweet"]
            media = []
            m = tw.get("media") or {}
            for item in (m.get("all") or m.get("photos") or []):
                media.append(item.get("url"))
            add_tweet(tweets, "fxtwitter", tw.get("id", tid), (tw.get("author") or {}).get("screen_name"), tw.get("text", ""), media, data)
        # vxtwitter shape
        elif "tweetID" in data:
            add_tweet(tweets, "vxtwitter", data.get("tweetID", tid), data.get("user_screen_name"), data.get("text", ""), data.get("mediaURLs") or [], data)
        notes.append(f"{u}: ok")
    return notes


def try_oembed(handle: str | None, tid: str, tweets: dict):
    if not handle:
        return "no handle"
    url = "https://publish.twitter.com/oembed?omit_script=true&url=" + urllib.parse.quote(f"https://twitter.com/{handle}/status/{tid}", safe="")
    try:
        data = json.loads(fetch(url, timeout=20))
        txt = strip_oembed_html(data.get("html", ""))
        # Trim attribution line if present but keep main text.
        txt = re.split(r"\n?—\s+", txt)[0].strip()
        add_tweet(tweets, "oembed", tid, handle, txt, raw=data)
        return "ok"
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def try_x_html(handle: str | None, tid: str, tweets: dict):
    url = f"https://x.com/{handle}/status/{tid}" if handle else f"https://x.com/i/status/{tid}"
    try:
        page = fetch(url, timeout=25)
    except Exception as e:
        return f"page fetch failed: {type(e).__name__}: {e}"
    count = 0
    # Embedded logged-out state often contains tweets.entities.{id} with full_text and media URLs.
    for m in re.finditer(r'"(\d{10,})":\{[^{}]{0,2000}?"full_text":"', page):
        obj_start = m.start(0) + len(m.group(1)) + 3
        # Use a small brace matcher from the opening { after the id.
        brace = page.find("{", m.start())
        depth = 0
        end = None
        in_str = False
        esc = False
        for i in range(brace, min(len(page), brace + 20000)):
            ch = page[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
        if not end:
            continue
        try:
            obj = json.loads(page[brace:end])
        except Exception:
            continue
        media = []
        for med in ((obj.get("extended_entities") or {}).get("media") or (obj.get("entities") or {}).get("media") or []):
            media.append(med.get("media_url_https") or med.get("media_url"))
        add_tweet(tweets, "x_embedded_html", obj.get("id_str", m.group(1)), handle, obj.get("full_text", ""), media, obj)
        count += 1
    return f"extracted {count} embedded tweet(s)"


def ocr_media(tweets: dict):
    if not shutil.which("tesseract"):
        return ["tesseract not installed; skipped OCR"]
    notes = []
    outdir = Path(tempfile.mkdtemp(prefix="x_media_"))
    for tw in tweets.values():
        tw["ocr"] = []
        for i, url in enumerate(tw.get("media", []), 1):
            if not url:
                continue
            # Ensure orig-ish URL works for pbs images.
            dl = url
            if "pbs.twimg.com/media/" in dl and "?" not in dl:
                dl += "?format=jpg&name=orig"
            img = outdir / f"{tw['id']}_{i}.jpg"
            try:
                img.write_bytes(fetch(dl, timeout=25, binary=True))
                p = subprocess.run(["tesseract", str(img), "stdout", "--psm", "6"], text=True, capture_output=True, timeout=45)
                txt = p.stdout.strip()
                if txt:
                    tw["ocr"].append({"url": url, "text": txt})
                notes.append(f"OCR {url}: {len(txt)} chars")
            except Exception as e:
                notes.append(f"OCR {url}: {type(e).__name__}: {e}")
    return notes


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    target = sys.argv[1]
    tid = extract_status_id(target)
    handle = extract_handle(target)
    tweets = {}
    notes = []
    notes.append("xurl: " + try_xurl(tid, tweets))
    notes += try_fx_vx(handle, tid, tweets)
    notes.append("oembed: " + try_oembed(handle, tid, tweets))
    notes.append("x_html: " + try_x_html(handle, tid, tweets))
    notes += ocr_media(tweets)
    result = {"target": target, "status_id": tid, "handle": handle, "tweets": list(tweets.values()), "notes": notes}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
