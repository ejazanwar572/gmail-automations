# HDFC Diners Club Black Metal (DCBM) Rewards Suite & Dashboard

A bespoke, production-grade credit card reward tracking system and interactive UI tailored specifically for **HDFC Diners Club Black Metal** card policies and SmartBuy multipliers.

---

## 🌟 Features & Architecture

### 1. Automated Real-Time Gmail Sync (`sync_alerts.py`)
- Connects directly to the Gmail API via OAuth.
- Ingests HDFC InstaAlert transaction emails.
- Auto-detects SmartBuy bookings:
  - **Flights (5X)**: 1X base (5 RP/₹150) + 4X bonus (20 RP/₹150).
  - **Hotels (10X)**: 1X base (5 RP/₹150) + 9X bonus (45 RP/₹150).
- Auto-extracts flight & hotel points redemptions from SmartBuy booking confirmations, deducting redeemed points from gross balances in real-time.

### 2. Cap Engine & Policy Guards (`dcbm_engine.py`)
- **Strict Calendar Month Accelerated Cap**: Tracks the 10,000 accelerated RP limit strictly from the 1st to the last day of each calendar month.
- **Reset Countdown**: Header badge showing exact days left until monthly cap reset (`⏳ Resets in 18 days`).
- **Daily Cap Guard**: Monitors the 2,500 RP per day accelerated cap limit.
- **Spend Buffer Headroom**: Real-time remaining spend capacity before hitting the 10,000 RP cap for SmartBuy Flights and Hotels.

### 3. Reward Points Portfolio & Valuation
- **Lifetime Reward Points**: Total points earned across all card spends to date.
- **Current Available Balance**: Net balance remaining after deducting burned points (valued at 1 RP = ₹1.00 on SmartBuy flights & hotels).
- **Net Reward Rate**: Cumulative percentage return on card spend (e.g., 8.61%).

### 4. Spend Milestones & Fee Waiver
- **Welcome Milestone**: ₹1.5 Lakhs in 90 days for Club Marriott, Amazon Prime, and Swiggy One memberships.
- **Quarterly Bonus Milestone**: ₹4 Lakhs quarterly spend for 10,000 Bonus RP with dynamic daily run-rate targets.
- **Annual Fee Waiver**: ₹8 Lakhs annual spend to waive the ₹10,000 annual membership fee.

### 5. Luxury Streamlit UI (`hdfc_dcbm_app.py`)
- **Haute Metal Theme**: Bespoke Champagne gold and bronze metallic design system.
- **Obsidian Dark Theme**: High-contrast luxury dark theme.
- **What-If Spend Simulator**: Calculate base points, accelerated points, daily cap status, and milestone progression before making any transaction.
- **Interactive Transaction & Redemption Ledgers**: Searchable, filterable tables with direct CSV export.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install streamlit pandas requests google-auth google-auth-oauthlib google-api-python-client
```

### 2. Launch the Dashboard
Using the launcher script:
```bash
./run_dashboard.sh
```
Or directly with Streamlit:
```bash
streamlit run hdfc_dcbm_app.py --server.port 8502
```
Open `http://localhost:8502` in your browser.

### 3. Sync Alerts from Gmail
Click the **Sync** button in the dashboard top navigation bar, or run:
```bash
python3 sync_alerts.py
```

### 4. Run Unit Tests
```bash
python3 -m unittest discover tests
```

---

## 📁 Folder Contents

```
HDFC Diners Black Metal Statements/
├── hdfc_dcbm_app.py         # Streamlit luxury dashboard UI
├── dcbm_engine.py           # Core points, cap, milestone & redemption engine
├── sync_alerts.py           # Gmail API alert & redemption parser
├── run_dashboard.sh         # Convenience launcher
├── card_config.json         # Card parameters, milestones & rates
├── tests/
│   ├── test_dcbm_engine.py  # Engine unit tests
│   └── test_sync_alerts.py  # Alert parser unit tests
└── README.md                # This documentation
```
