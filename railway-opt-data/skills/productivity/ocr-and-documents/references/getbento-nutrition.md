# GetBento / restaurant nutritional PDFs

Session notes:
- For restaurant menus hosted on GetBento, a direct PDF URL may be available in multiple versions; use `web_search` with `site:getbento.com` plus the item name to surface the latest guide and exact line-item snippets.
- `web_extract` often returns a usable markdown summary, but search-result snippets can expose the exact nutrition row when the document is large or OCR is partial.
- Example item mappings found in NAYA guide (updated 11/21/24 / 26_0407 variants):
  - Chicken Shawarma: 190 cal, 4 oz, 23g protein, 280mg sodium
  - Cucumber Yogurt: 35 cal, 1 oz, 1g protein, 35mg sodium
  - Hummus: 140 cal, 2.5 oz, 4g protein, 270mg sodium
  - Feta Cheese: 70 cal, 1 oz, 4g protein, 260mg sodium
  - Pickled Turnips: 5 cal, 1 oz
  - Spicy Red Pepper Sauce: 45 cal, 1 oz, 260mg sodium
- When the user asks for a composed meal, total the visible line items and call out any assumptions about base/grain and sauce portions.