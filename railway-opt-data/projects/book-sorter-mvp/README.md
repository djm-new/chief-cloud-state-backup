# Book Sorter MVP

Mobile-first gallery for reviewing one or more floor photos of kids' books.

## Included
- `books_sorter.py` — small FastAPI helper that serves the page and demo photo
- `assets/books_sorter.html` — self-contained mobile UI
- `assets/books-sorter-demo.jpg` — sample floor photo

## Behavior
- Detects individual books from the sample photo
- Shows a gallery grid optimized for phones
- Green check = keep
- Red X = discard
- Blank = undecided
- Tap center to enlarge
- Duplicate detections are grouped with a count badge
- Category suggestions: coloring, activity, sticker

## Notes
This folder is a durable GitHub-backed copy of the MVP artifacts while we finalize the proper Hermes deployment wiring.
