# 🛒 Instamart Alerts - Swiggy Instamart Live Price Tracker

An automated grocery price tracking and discount alerting engine built for Swiggy Instamart. It automatically scrapes product listings, tracks price histories in an SQLite database, filters for discounts > 20%, and delivers mobile-responsive HTML email alerts straight to your inbox.

---

## Key Features

1. **Automated Web Scraper (`instamart_scraper.py`)**:
   - Built with Selenium Stealth and BeautifulSoup.
   - Sets delivery location (`HSR Layout Bangalore` by default).
   - Executes `scrollIntoView()` infinite scrolling to load full product catalogs (up to 140+ items per category).
   - Per-query exception isolation & direct search URL fallbacks to ensure 100% resilient runs without crashes.

2. **Location & Watchlist Configuration**:
   - Easily manage your delivery locations and keyword watchlist by editing the top-level lists in `instamart_scraper.py`:
     ```python
     # Tracked Delivery Locations (Add as many locations as you want!)
     TRACKED_LOCATIONS = [
         "HSR Layout Bangalore",
         # "Koramangala Bangalore",
         # "Indiranagar Bangalore",
     ]

     # Watchlist Keywords
     TRACKED_KEYWORDS = [
         "milk",
         "mustard oil",
         "eggs",
         "oil",
         "soap",
         "shampoo",
         "sugar",
         "coffee",
     ]
     ```


3. **SQLite Historical Price Database (`instamart_prices.db`)**:
   - Tracks timestamped price snapshots with primary key `(product_id, location, scraped_at)`.
   - Uses clean, unique product slugs (e.g. `nandini-pasteurised-toned-milk-500-ml`).

4. **Instant SQL Price Drop Engine (`--compare` / `-c`)**:
   - Calculates price drops using the SQL `LAG()` window function.
   - Evaluates strictly the **latest scraped snapshot** of each product using `ROW_NUMBER() OVER (PARTITION BY product_id, location ORDER BY scraped_at DESC) WHERE rn = 1` (preventing duplicate alerts for stabilized items).
   - Filters for items with **> 20% price drops** (`WHERE price < 0.8 * previous_price`).
   - Sorts listings in descending order of absolute rupee savings (`ORDER BY price_drop DESC`).
   - Includes direct clickable Swiggy Instamart web links (`https://www.swiggy.com/instamart/search?query=...`) for instant purchase.

5. **Mobile Smartphone HTML Email Alerts**:
   - Delivers styled HTML product cards tailored for smartphone screens (iOS & Android Gmail apps).
   - Features green savings badges (`Save ₹421 • 41% OFF`) and full-width orange **[🛒 View Item on Instamart]** buttons.
   - Triggers **only** when price drops exist (`if not rows: return`).

6. **Hourly Cloud Automation (GitHub Actions)**:
   - Automated hourly GitHub Actions cron (`0 * * * *`) running on $0 free tier for public repository.
   - Auto-commits updated `instamart_prices.db` snapshots back to git.

---

## CLI Usage Commands

Navigate to the `Instamart Alerts` folder:

```bash
cd "Instamart Alerts"
```

### 1. Live Scrape & Email Alert Run
Live scrapes all watchlist items for HSR Layout Bangalore and sends an HTML email alert if discounts > 20% exist:
```bash
python3 instamart_scraper.py
```

### 2. Live Scrape Custom Location / Query
Scrape a specific location or single product category:
```bash
python3 instamart_scraper.py --location "Indiranagar Bangalore" "milk"
```

### 3. Instant Database Price Drop Comparison
Run offline database comparison without opening Chrome:
```bash
python3 instamart_scraper.py --compare
```

### 4. Comparison for Specific Location
```bash
python3 instamart_scraper.py --location "HSR Layout Bangalore" --compare
```

---

## Project Structure

```text
Instamart Alerts/
├── instamart_scraper.py   # Main scraper, SQL comparison engine & email alert trigger
├── instamart_prices.db    # SQLite price history database
├── .env                   # Local email credentials (ignored by Git)
└── README.md              # Documentation
```
