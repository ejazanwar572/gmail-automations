# Gmail Automations, Job Matcher & Instamart Price Suite

A comprehensive personal utility suite that automates finance tracking (credit card statement validations, cashbacks, and expenses), runs an AI career portal scraper, and features an automated Swiggy Instamart live price tracker with mobile HTML email alerts.

---

## Repository Overview

This repository contains several automated pipelines organized into modular scripts:

### 1. 🛒 Swiggy Instamart Live Price Tracker & Scraper (`Instamart Alerts/`)
* **Dedicated Subfolder**: [`Instamart Alerts/`](file:///Users/ejazanwar/Documents/Gmail%20Automations/Instamart%20Alerts) (Contains its own standalone [`Instamart Alerts/README.md`](file:///Users/ejazanwar/Documents/Gmail%20Automations/Instamart%20Alerts/README.md)).
* **Automated Scraper (`Instamart Alerts/instamart_scraper.py`)**: Headless Chrome scraper using Selenium Stealth & BeautifulSoup. It sets delivery locations, searches Swiggy Instamart, and executes `scrollIntoView()` infinite scrolling to load full product catalogs (up to 140+ items per category).
* **Location & Watchlist**:
  * **Default Location**: `HSR Layout Bangalore` (Override via `--location "Neighborhood City"`).
  * **Watchlist Keywords (`TRACKED_KEYWORDS`)**: Configurable python list (`milk`, `mustard oil`, `eggs`, `oil`, `soap`, `shampoo`).
* **SQLite Price Database (`Instamart Alerts/instamart_prices.db`)**: Stores historical timestamped price snapshots with composite primary key `(product_id, location, scraped_at)`.
* **Mobile HTML Email Alerts**: Delivers mobile-responsive HTML cards with green savings badges and direct purchase buttons to `anwar.ejaz181@gmail.com` via Gmail SMTP (**only** when price drops exist).
* **Hourly Cloud Automation (`.github/workflows/instamart_scraper.yml`)**: Automated hourly GitHub Actions cron (`0 * * * *`) running on $0 free tier, auto-committing updated `Instamart Alerts/instamart_prices.db` snapshots back to git.

#### Instamart Scraper CLI Commands:
```bash
cd "Instamart Alerts"

# Live scrape all watchlist items & send HTML email on > 20% price drops
python3 instamart_scraper.py

# Instant offline database price drop comparison
python3 instamart_scraper.py --compare
```


---

### 2. 💼 Job Matcher & Scraper
* **Scraper (`check_job_boards.py`)**: Crawls career portals across Greenhouse, Phenom, Jibe, Workday, SmartRecruiters, WordPress, and custom HTML platforms with location pre-filtering (prioritizing Bangalore first, then India/Remote).
* **AI Matcher (`evaluate_jobs_github.py`)**: Executes scraper, scores listings (0-100) against resume using Gemini API, logs history to `job_matches_report.md`, and emails HTML briefs for high-matching roles (&ge; 70%).
* **Automation (`.github/workflows/job_matcher.yml`)**: GitHub Actions workflow running automatically every 2 hours.

---

### 3. 💳 Credit Card Bill & Cashback Trackers
* **Axis Airtel & Flipkart CC (`Airtel Axis Statements/` & `Flipkart Axis Statements/`)**: Syncs transaction alerts from Gmail, downloads billing statements, validates transactions against PDF line-items, and generates cashback cap progress reports.
* **SBI Cashback CC (`SBI Cashback Statements/`)**: Validates and maps cashback alerts against downloaded statement PDFs to track spend caps.
* **Cashback Workflow (`combined_cashback_workflow.py`)**: Unifies the execution of multiple cashback validations.

---

### 4. 📊 Expense Tracker & Dashboard
* **Expense Ledger (`ai_expense_tracker.py` & `local_expense_tracker.py`)**: Programmatically parses UPI debit and payment emails to maintain a local SQLite expense database.
* **Visual Dashboard (`dashboard.py`)**: Web-based analytical dashboard displaying card spends, categories, remaining cap limits, and matching job listings.

---

## Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ejazanwar572/gmail-automations.git
   cd gmail-automations
   ```

2. **Configure Environment Variables (`.env`)**:
   Create a local `.env` file (ignored by `.gitignore`):
   ```bash
   SENDER_EMAIL=anwar.ejaz181@gmail.com
   SENDER_PASSWORD=your-16-char-gmail-app-password
   RECIPIENT_EMAIL=anwar.ejaz181@gmail.com
   GEMINI_API_KEY=your-gemini-api-key
   ```

3. **Install Dependencies**:
   ```bash
   pip install selenium beautifulsoup4 google-generativeai
   ```

4. **Run Trackers**:
   ```bash
   # Run Instamart Tracker
   python3 instamart_scraper.py

   # Run Job Matcher
   python3 evaluate_jobs_github.py
   ```

---

## GitHub Actions Secrets Setup

Configure Encrypted Secrets in GitHub Repository Settings (**Settings** &rarr; **Secrets and variables** &rarr; **Actions**):
* `SENDER_EMAIL`: Gmail sender address (`anwar.ejaz181@gmail.com`).
* `SENDER_PASSWORD`: 16-character Gmail App Password.
* `RECIPIENT_EMAIL`: Recipient email (`anwar.ejaz181@gmail.com`).
* `GEMINI_API_KEY`: Google Gemini API Key for Job Matcher.
