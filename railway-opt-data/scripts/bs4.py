"""Minimal BeautifulSoup-compatible shim for Hermes scripts.

Implements just enough for calls like:
    from bs4 import BeautifulSoup
    BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)

This keeps the live cron venv working without the external bs4 package.
"""
from __future__ import annotations

import re
import html as _html


class BeautifulSoup:
    def __init__(self, markup: str, parser: str | None = None):
        self.markup = str(markup or '')

    def get_text(self, separator: str = '', strip: bool = False) -> str:
        text = _html.unescape(re.sub(r'<[^>]+>', ' ', self.markup))
        text = re.sub(r'\s+', ' ', text)
        if strip:
            text = text.strip()
        if separator and separator != ' ':
            text = separator.join(text.split())
        return text
