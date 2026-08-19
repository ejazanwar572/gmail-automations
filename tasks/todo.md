# Amazon Price Tracker Implementation Checklist

- [x] Create `amazon_products.json` containing the 23 active tracked products with ASINs, clean titles, categories, baseline prices, and target price thresholds
- [x] Implement `amazon_price_tracker.py` with:
  - Standard-library resilient HTTP fetcher (custom browser user-agent, retry backoff)
  - Price, availability, and title parsers for Amazon product pages
  - SQLite database `amazon_prices.db` for timestamped historical price snapshots
  - Price drop detection engine (comparing against baseline and previous checks)
  - Markdown and console reporting formatters
- [x] Implement standalone test suite `tests/test_amazon_tracker.py` to verify:
  - Product loading and normalization
  - SQLite schema creation and price history recording
  - Price drop calculation and alerting logic
- [x] Run end-to-end check on tracked products and verify database logging
- [x] Document usage instructions and scheduled automation options in walkthrough


