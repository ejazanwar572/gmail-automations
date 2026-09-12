# Gmail Automations, Job Matcher & Personal Intelligence Suite

A comprehensive personal utility and intelligence suite that automates finance tracking (credit card reward engines, cashback cap validations, and expenses), runs an AI career portal scraper, and features an automated Swiggy Instamart live price tracker with mobile HTML alerts.

---

## 📂 Repository Overview & Modules

This repository contains several automated pipelines organized into dedicated folders:

### 1. 💳 Credit Card Rewards & Cashback Trackers

* **🌟 HDFC Diners Club Black Metal (`HDFC Diners Black Metal Statements/`)**:
  * **Dedicated Documentation**: See [`HDFC Diners Black Metal Statements/README.md`](HDFC%20Diners%20Black%20Metal%20Statements/README.md).
  * **Interactive Streamlit Dashboard**: Luxury Haute Metal (Light) and Obsidian (Dark) interface.
  * **Core Engine**: Real-time Gmail InstaAlert sync, SmartBuy 5X/10X multiplier detection, calendar month 10,000 accelerated cap tracker with countdown (`⏳ Resets in 18 days`), 2,500 daily cap guard, milestone progress (Welcome, Quarterly 10k Bonus, Annual Fee Waiver), and automated SmartBuy flight/hotel redemption tracking.
  * **Launch**:
    ```bash
    cd "HDFC Diners Black Metal Statements"
    ./run_dashboard.sh
    ```
* **HSBC Live Plus CC (`HSBC Live Plus Statements/`)**: 10% cashback tracking on dining, food delivery, and groceries (₹1,000 monthly cap).
* **Axis Airtel & Flipkart CC (`Airtel Axis Statements/` & `Flipkart Axis Statements/`)**: Syncs transaction alerts from Gmail, validates statements against PDF line-items, and generates cashback cap progress reports.
* **SBI Cashback CC (`SBI Cashback Statements/`)**: Validates and maps cashback alerts against statements to track 5% online spend caps.
* **Combined Cashback Workflow (`combined_cashback_workflow.py`)**: Unifies the execution of multiple cashback validations.

---

### 2. 🛒 Swiggy Instamart Live Price Tracker & Scraper (`Instamart_Alerts/`)
* **Dedicated Subfolder**: [`Instamart_Alerts/`](Instamart_Alerts/) (Contains its own standalone [`Instamart_Alerts/README.md`](Instamart_Alerts/README.md)).
* **Automated Scraper (`Instamart_Alerts/instamart_scraper.py`)**: Headless Chrome scraper using Selenium Stealth & BeautifulSoup. Sets delivery locations, searches Swiggy Instamart, and executes infinite scrolling to load full product catalogs.
* **Location & Watchlist**:
  * **Default Location**: `HSR Layout Bangalore` (Override via `--location "Neighborhood City"`).
  * **Watchlist Keywords**: Configurable list (`milk`, `mustard oil`, `eggs`, `oil`, `soap`, `shampoo`, etc.).
* **SQLite Price Database**: Stores historical timestamped price snapshots with composite primary key `(product_id, location, scraped_at)`.
* **Mobile HTML Email Alerts**: Delivers mobile-responsive HTML cards with green savings badges and direct purchase buttons via Gmail SMTP (only when price drops exist).
* **Cloud Automation (`.github/workflows/instamart_scraper.yml`)**: GitHub Actions workflow running on schedule.

---

### 3. 💼 Job Matcher & Career Scraper
* **Scraper (`check_job_boards.py`)**: Crawls career portals across Greenhouse, Phenom, Jibe, Workday, SmartRecruiters, WordPress, and custom platforms with location pre-filtering (prioritizing Bangalore first, then India/Remote).
* **AI Matcher (`evaluate_jobs_github.py`)**: Executes scraper, scores listings (0-100) against resume using Gemini API, logs history to `job_matches_report.md`, and emails HTML briefs for high-matching roles (&ge; 70%).
* **Radar Dashboard (`job_radar_dashboard.py`)**: Interactive Streamlit dashboard for filtering, reviewing, and tracking scraped job applications.
* **Automation (`.github/workflows/job_matcher.yml`)**: GitHub Actions workflow running automatically on schedule.

---

### 4. 📊 Expense Tracker & Ledger
* **Expense Ledger (`ai_expense_tracker.py` & `local_expense_tracker.py`)**: Programmatically parses UPI debit and payment emails to maintain a local SQLite expense database.
* **Visual Dashboard (`dashboard.py`)**: Web-based analytical dashboard displaying card spends, categories, remaining cap limits, and matching job listings.

---

## 🔒 Security & Credential Hygiene

This repository strictly enforces confidentiality and credential segregation via `.gitignore`:
- `credentials*.json`: Google Cloud OAuth client secrets (strictly ignored).
- `token*.json`: OAuth user access and refresh tokens (strictly ignored).
- `.env`, `.env.*`: Local environment variables and passwords (strictly ignored).
- `*.pdf`: Credit card statement PDFs (strictly ignored).
- `*cache.json`: Local alert and redemption caches (strictly ignored).

---

## 🚀 Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ejazanwar572/gmail-automations.git
   cd gmail-automations
   ```

2. **Configure Environment Variables (`.env`)**:
   Create a local `.env` file (ignored by git):
   ```bash
   SENDER_EMAIL=anwar.ejaz181@gmail.com
   SENDER_PASSWORD=your-16-char-gmail-app-password
   RECIPIENT_EMAIL=anwar.ejaz181@gmail.com
   GEMINI_API_KEY=your-gemini-api-key
   ```

3. **Install Dependencies**:
   ```bash
   pip install streamlit pandas requests selenium beautifulsoup4 google-auth google-auth-oauthlib google-api-python-client google-generativeai
   ```

---

## 📜 License
Private personal project. Built for personal automated financial intelligence, price alerts, and career scanning.
