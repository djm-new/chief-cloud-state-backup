"""Book sorter landing page and demo asset helpers."""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse, HTMLResponse

ASSET_DIR = Path(__file__).with_name("assets")
BOOKS_SORTER_HTML = ASSET_DIR / "books_sorter.html"
BOOKS_SORTER_DEMO_PHOTO = ASSET_DIR / "books-sorter-demo.jpg"


def books_sorter_page() -> HTMLResponse:
    return HTMLResponse(
        BOOKS_SORTER_HTML.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


def books_sorter_demo_photo() -> FileResponse:
    return FileResponse(BOOKS_SORTER_DEMO_PHOTO)
