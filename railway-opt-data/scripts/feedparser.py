"""Minimal local feedparser-compatible shim for Hermes scripts.

Supports the subset of the third-party `feedparser` API used by our podcast
collection scripts:
- parse(url_or_text) -> object with `.entries`, `.bozo`, `.bozo_exception`
- entry fields: title, summary/description, link, id, published/updated,
  published_parsed/updated_parsed, enclosures, links, itunes_duration

This is intentionally small and dependency-free so cron jobs keep working even
when the live venv cannot install external packages.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests


@dataclass
class FeedResult:
    entries: list[dict[str, Any]]
    bozo: bool = False
    bozo_exception: Exception | None = None


def _strip_ns(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in tag else tag


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ''
    return ''.join(el.itertext()).strip()


def _dt_to_struct(dt: datetime | None):
    if not dt:
        return None
    return dt.utctimetuple()


def _parse_dt(value: str | None):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    try:
        cleaned = value.replace('Z', '+00:00')
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _load_xml(source: str) -> tuple[str, ET.Element]:
    parsed = urlparse(source)
    if parsed.scheme in {'http', 'https'}:
        resp = requests.get(source, headers={'User-Agent': 'HermesFeedParser/0.1'}, timeout=30)
        resp.raise_for_status()
        return resp.text, ET.fromstring(resp.content)
    if '<' in source[:2000]:
        return source, ET.fromstring(source)
    text = open(source, 'r', encoding='utf-8').read()
    return text, ET.fromstring(text)


def _build_entry(item: ET.Element) -> dict[str, Any]:
    entry: dict[str, Any] = {}
    links = []
    enclosures = []

    for child in list(item):
        tag = _strip_ns(child.tag).lower()
        text = _text(child)
        if tag in {'title', 'summary', 'description', 'link', 'id', 'guid', 'published', 'updated'}:
            if tag == 'guid':
                entry.setdefault('id', text)
            elif tag == 'description':
                entry.setdefault('summary', text)
                entry.setdefault('description', text)
            else:
                entry.setdefault(tag, text)
        elif tag == 'encoded':
            entry.setdefault('summary', text)
        elif tag == 'duration':
            entry.setdefault('itunes_duration', text)
        elif tag == 'enclosure':
            href = child.attrib.get('url') or child.attrib.get('href') or ''
            if href:
                enc = {
                    'href': href,
                    'type': child.attrib.get('type', ''),
                    'length': child.attrib.get('length', ''),
                }
                enclosures.append(enc)
        elif tag == 'link':
            href = child.attrib.get('href') or text
            if href:
                links.append({
                    'href': href,
                    'rel': child.attrib.get('rel', 'alternate'),
                    'type': child.attrib.get('type', ''),
                })

    if links:
        entry['links'] = links
        if not entry.get('link'):
            entry['link'] = next((l.get('href') for l in links if l.get('rel') in {'alternate', ''}), links[0].get('href', ''))
    if enclosures:
        entry['enclosures'] = enclosures
        if not entry.get('links'):
            entry['links'] = []
        entry['links'].extend({
            'href': e.get('href', ''),
            'rel': 'enclosure',
            'type': e.get('type', ''),
        } for e in enclosures)

    for field in ('published', 'updated'):
        dt = _parse_dt(entry.get(field))
        if dt:
            entry[f'{field}_parsed'] = _dt_to_struct(dt)

    if not entry.get('id'):
        entry['id'] = entry.get('link') or entry.get('title') or ''
    return entry


def parse(source: str) -> FeedResult:
    try:
        _, root = _load_xml(source)
        tag = _strip_ns(root.tag).lower()
        entries: list[dict[str, Any]] = []

        if tag == 'rss':
            channel = next((c for c in list(root) if _strip_ns(c.tag).lower() == 'channel'), root)
            for item in list(channel):
                if _strip_ns(item.tag).lower() == 'item':
                    entries.append(_build_entry(item))
        elif tag == 'feed':
            for item in list(root):
                if _strip_ns(item.tag).lower() == 'entry':
                    entries.append(_build_entry(item))
        else:
            for item in list(root):
                if _strip_ns(item.tag).lower() in {'item', 'entry'}:
                    entries.append(_build_entry(item))

        return FeedResult(entries=entries, bozo=False, bozo_exception=None)
    except Exception as e:
        return FeedResult(entries=[], bozo=True, bozo_exception=e)
