# Gmail Automations & Credit Card Reward Suites

A high-performance personal automation and intelligence suite featuring real-time credit card rewards tracking, milestone engines, Gmail alert sync, and luxury Streamlit dashboards.

---

## 🌟 Flagship Feature: HDFC Diners Club Black Metal (DCBM) Dashboard

A production-grade, bespoke rewards tracking system and interactive UI tailored specifically for the **HDFC Diners Club Black Metal** credit card rules and SmartBuy multipliers.

### Key Capabilities

1. **Automated Real-Time Gmail Sync**:
   - Directly connects to Gmail API to fetch HDFC InstaAlert transaction emails.
   - Automatically detects SmartBuy bookings (Flights 5X, Hotels 10X) and regular spends.
   - Automatically parses flight and hotel points redemption confirmations, deducting burned points from gross balances in real-time.

2. **Policy-Accurate Cap & Reset Tracking**:
   - **Strict Calendar Month Accelerated Cap**: Tracks the 10,000 accelerated RP limit strictly from the 1st to the last day of each calendar month.
   - **Reset Countdown**: Prominent header badge indicating exact days until monthly reset (`⏳ Resets in 18 days`).
   - **Daily Guard**: Monitors the 2,500 RP per day accelerated cap limit.
   - **Remaining Headroom**: Live rupee spend buffers before hitting the 10k cap for SmartBuy Flights (5X) and Hotels (10X).

3. **Consolidated Reward Points Portfolio**:
   - **Lifetime Reward Points**: Total points earned across all card spends to date.
   - **Current Available Balance**: Net balance remaining after deducting burned points (valued at 1 RP = ₹1.00 on SmartBuy).
   - **Net Reward Rate**: Cumulative percentage return on card spend (e.g., 8.61%).

4. **Spend Milestones & Fee Waiver Engine**:
   - **Welcome Milestone**: ₹1.5 Lakhs in 90 days for Club Marriott, Amazon Prime, and Swiggy One memberships.
   - **Quarterly Bonus Milestone**: ₹4 Lakhs quarterly spend for 10,000 Bonus RP with dynamic daily run-rate targets.
   - **Annual Fee Waiver**: ₹8 Lakhs annual spend to waive the ₹10,000 annual membership fee.

5. **Design System & UX**:
   - **Haute Metal Light Theme**: Bespoke Champagne gold, warm ivory, and bronze metallic aesthetics.
   - **Obsidian Dark Theme**: High-contrast dark luxury metallic theme.
   - **What-If Spend Simulator**: Calculate base points, accelerated points, daily cap status, and milestone progression before making any transaction.
   - **Transaction & Redemption Ledgers**: Searchable, filterable tables with direct CSV export.

---

## 🚀 Quick Start: Running the DCBM Dashboard

### Prerequisites
- Python 3.10+
- Chrome / Chromium (if capturing headless browser previews)

### 1. Install Dependencies
```bash
pip install streamlit pandas requests google-auth google-auth-oauthlib google-api-python-client
```

### 2. Launch the Dashboard
Using the convenient launch script:
```bash
./run_dcbm_dashboard.sh
```
Or directly with Streamlit:
```bash
streamlit run "HDFC Diners Black Metal Statements/hdfc_dcbm_app.py" --server.port 8502
```
Access the application at `http://localhost:8502`.

### 3. Sync Alerts from Gmail
Click the **Sync** button directly inside the dashboard UI, or run the standalone sync script:
```bash
python3 "HDFC Diners Black Metal Statements/sync_alerts.py"
```

### 4. Run Unit Tests
Run the comprehensive test suite (33+ unit tests):
```bash
python3 -m unittest discover "HDFC Diners Black Metal Statements/tests"
```

---

## 🔒 Security & Credential Hygiene

This repository strictly enforces confidentiality and credential segregation:

| File Pattern | Description | Git Status |
| :--- | :--- | :--- |
| `credentials*.json` | Google Cloud OAuth client secrets | **Ignored** (`.gitignore`) |
| `token*.json` | OAuth user access and refresh tokens | **Ignored** (`.gitignore`) |
| `.env`, `.env.*` | Local environment variables & passwords | **Ignored** (`.gitignore`) |
| `*.pdf` | Credit card statement PDFs | **Ignored** (`.gitignore`) |
| `*cache.json` | Local alert and redemption caches | **Ignored** (`.gitignore`) |

No API keys, OAuth tokens, personal statement PDFs, or client secrets are ever checked into source control.

---

## 📁 Repository Structure

```
.
├── HDFC Diners Black Metal Statements/
│   ├── hdfc_dcbm_app.py           # Streamlit luxury dashboard UI
│   ├── dcbm_engine.py             # Core points, cap, milestone & redemption engine
│   ├── sync_alerts.py             # Gmail API alert & redemption parser
│   ├── tests/
│   │   ├── test_dcbm_engine.py    # Engine unit tests
│   │   └── test_sync_alerts.py    # Alert parser unit tests
│   └── card_config.json           # Card parameters, milestones & rates
├── Airtel Axis Statements/         # Airtel Axis cashback tracker & statement validator
├── Flipkart Axis Statements/       # Flipkart Axis cashback tracker & validator
├── HSBC Live Plus Statements/      # HSBC Live Plus dining/grocery cashback tracker
├── SBI Cashback Statements/        # SBI Cashback 5% online spend validator
├── Instamart_Alerts/              # Swiggy Instamart live price scraper & drop alert system
├── run_dcbm_dashboard.sh          # One-click launcher for the DCBM dashboard
├── .gitignore                     # Rigorous credential & data ignore rules
└── README.md                      # Repository documentation
```

---

## 🛠️ Other Credit Card Trackers

In addition to DCBM, this repository contains automated cashback tracking for:
- **HSBC Live Plus**: 10% cashback on dining, food delivery, and groceries (₹1,000 monthly cap).
- **Airtel Axis**: 25% on Airtel recharge, 10% on utilities & Swiggy/Zomato/BigBasket.
- **Flipkart Axis**: 5% unlimited cashback on Flipkart & Myntra.
- **SBI Cashback**: 5% online shopping cashback tracking (₹5,000 monthly cap).

---

## 📜 License
Private personal project. Built for automated financial intelligence and real-time rewards optimization.
