# 🛒 Amazon India Price Tracker

Automated price tracking and monitoring system for recurring Amazon India purchases. Tracks public product pages, records historical prices in SQLite, detects discounts / all-time lows, and produces formatted reports.

---

## 📂 Folder Structure

```
Amazon_Price_Tracker/
├── amazon_price_tracker.py      # Main tracking and reporting script
├── amazon_products.json         # Configured list of tracked products & target prices
├── amazon_prices.db             # SQLite database storing price snapshots
├── reports/
│   └── amazon_price_report.md   # Auto-generated markdown report
└── tests/
    └── test_amazon_tracker.py   # Unit test suite
```

---

## 🚀 Usage

### 1. View Tracked Items
```bash
python3 Amazon_Price_Tracker/amazon_price_tracker.py --list
```

### 2. Run Live Price Check (Scrapes & Updates SQLite)
```bash
python3 Amazon_Price_Tracker/amazon_price_tracker.py --check
```

### 3. Generate Markdown Report
```bash
python3 Amazon_Price_Tracker/amazon_price_tracker.py --report
```

### 4. Check Single Item
```bash
python3 Amazon_Price_Tracker/amazon_price_tracker.py --asin B0GPRPQF23
```

---

## ⏰ Cron Job Example (Daily 9:00 AM)
```text
0 9 * * * /usr/bin/python3 "/Users/ejazanwar/Documents/Gmail Automations/Amazon_Price_Tracker/amazon_price_tracker.py" --check >> "/Users/ejazanwar/Documents/Gmail Automations/Amazon_Price_Tracker/reports/cron.log" 2>&1
```
