# Implementation Plan: DCBM Dashboard UI Revamp with Reflex

## Objective
Build and test a modern, responsive web application prototype for the HDFC Diners Club Black Metal Control Center using [Reflex](https://github.com/reflex-dev/reflex) (pure Python compiling to Next.js, Radix UI, and Tailwind CSS), powered directly by `dcbm_engine.py`.

---

## Phase 1: Environment & Scaffolding
- [x] Install Reflex in the Python environment (`pip install reflex` -> v0.10.1)
- [x] Verify prerequisites: Python 3.12, Node.js (v22 installed), Reflex CLI (`reflex --version`)
- [x] Initialize Reflex project `dcbm_reflex` inside `/Users/ejazanwar/Documents/Gmail Automations/dcbm_reflex`
- [x] Configure `rxconfig.py` with app name, theme, and port configurations

---

## Phase 2: State Architecture & Engine Integration
- [x] Create `dcbm_reflex/state.py`:
  - Define `DCBMState(rx.State)` with Pydantic models (`TxItem`, `MonthHistoryItem`, `RedemptionItem`)
  - Connect to `HDFC Diners Black Metal Statements/dcbm_engine.py` without code duplication
  - Load and compute dashboard data (`caps`, `milestones`, `points_summary`, `transactions`, `monthly_history`, `redemptions`)
  - Implement reactive properties: category filter, cycle/month filter, merchant search query, active tab selection
  - Implement live Gmail sync event handler with toast notifications and background async handling

---

## Phase 3: Component Engineering (Radix UI & Tailwind in Python)
- [x] **Navigation & Header Bar**:
  - Account info, masked card badge (`•••• 2360`), status pill, live sync timestamp, dark/light theme switch, and interactive sync button.
- [x] **Hero Section (Bento Grid)**:
  - Card 1: 10,000 Accelerated RP Monthly Limit (progress indicator, remaining RP, days remaining).
  - Card 2: Spend Headroom (5X SmartBuy Flights capacity, 10X Hotels capacity).
  - Card 3: Portfolio & Reward Rate (Lifetime RP, available SmartBuy value, effective reward rate %).
- [x] **Milestones Row**:
  - Welcome Milestone (₹1.5L / 90d), Quarterly Milestone (₹4L / 10k bonus RP), Annual Fee Waiver (₹8L / save ₹10k fee).
- [x] **Interactive Tabs & Data Tables**:
  - Tab 1: Live Transactions Ledger with dynamic category filter pills, merchant search input, summary metric badges, and transaction data table.
  - Tab 2: Monthly History & Cap Utilization Table with inline cap progress bars.
  - Tab 3: Points Redemptions Table with direct savings and booking value breakdown.
- [x] **Theme & Polish**:
  - Executive metallic palette (Champagne Gold, Onyx, Slate), responsive grid layouts, card hover micro-animations.

---

## Phase 4: Local Compilation, Testing & Verification
- [x] Compile and launch the app via `reflex run`
- [x] Verify Next.js frontend builds cleanly and serves on `localhost:3000` (backend on `localhost:8000`)
- [x] Test interactions: tab switching, category filtering, search, data rendering accuracy
- [x] Verify data parity against the existing Streamlit dashboard (`dcbm_engine` source of truth)
- [x] Verified in browser with full visual screenshots:
  - Desktop light mode overview
  - Scrolled transactions ledger
  - Monthly history & cap utilization tab
  - Points redemptions tab
  - One-click dark mode toggle (Champagne & Onyx)
  - Real-time reactive instant search filtering ("flight" query with dynamic KPI chip recalculation)

---

## Phase 5: Architecture Review & Comparison: Streamlit vs Reflex

| Criterion | Existing Streamlit Implementation | Reflex Implementation (`dcbm_reflex`) |
| :--- | :--- | :--- |
| **Frontend Architecture** | Python script rerun model; HTML string interpolation & 500+ lines of brittle CSS targeting `[data-testid]` | Real React + Next.js + Radix UI + Tailwind CSS compiled automatically from pure Python |
| **State & Interactivity** | Full script re-execution on widget changes; can cause UI jumps / flicker | WebSocket reactive state diffing; sub-10ms instant DOM updates without page flashing |
| **UI Components** | Fixed-height CSS containers (`height: 240px`), hacky selectboxes | Native Radix cards, badges, tabs, progress bars, and tables with automatic fluid responsiveness |
| **Dark / Light Mode** | Custom CSS override clashes; theme switching requires complex CSS variables | Built-in zero-config Radix theme toggle (`rx.color_mode.button()`) syncing with system preference |
| **Data Grid & Tables** | `st.dataframe` or third-party AgGrid wrapper | Native semantic Radix HTML tables with badges, inline progress bars, monospace codes, and custom cells |
| **Source of Truth** | Directly calls `dcbm_engine.py` | Directly calls `dcbm_engine.py` (100% data parity preserved) |

---

## Phase 6: HSBC Live+ Page & Multi-Card Control Center
- [x] Extend Reflex state model in `dcbm_reflex/state.py`:
  - `active_card: str = "HDFC"` (supports "HDFC" and "HSBC")
  - `HSBCTxItem` model with fields (`date`, `merchant`, `category`, `mcc`, `rate`, `is_accelerated`, `cashback_earned`, `evidence`, `source`)
  - HSBC metrics: cycle (14 Oct - 13 Nov), monthly cap (₹1,200), remaining cap (₹481.20), headroom (₹4,812 dining/grocery), portfolio (₹4,634.33 cashback, 5.87%), milestones (Welcome ₹20k, Annual Fee ₹2L), and lounge perks.
  - Reactive filter properties for HSBC transactions (search, category pills, cycle filter).
  - HSBC Gmail sync handler with toast feedback.
- [x] Build HSBC Reflex components:
  - Header segmented control: `[💳 HDFC Diners Metal]  [💳 HSBC Live+]`
  - `components/hsbc_hero.py`: Bento grid with ₹1,200 Cashback Cap, ₹4,812 Dining/Grocery Headroom, and 5.87% Net Reward Rate.
  - `components/hsbc_milestones.py`: Welcome Milestone (₹20k), Annual Fee Waiver (₹2L), Airport Lounge & Roaming Perks.
  - `components/hsbc_tabs.py`: Live HSBC transactions ledger with search, category filtering, MCC codes, and cashback badges.
- [x] Update `dcbm_reflex.py` to conditionally render active card components.
- [x] Verify local compilation and visual quality in browser (Light, Dark mode, Grocery filtering).

---

## Phase 7: Deployment to Web on a Separate URL
- [x] Ensure `HDFC Diners Black Metal Statements/hdfc_dcbm_app.py` is 100% untouched to preserve existing URL (`https://ejaz-dcbm-report.streamlit.app/`).
- [x] Provide multi-card modernized version `card_control_center_v2.py` ready for Streamlit Cloud deployment under a separate URL (e.g. `ejaz-cards-v2.streamlit.app`).
- [x] Add root `.gitignore` protecting credentials, `.env`, logs, and build directories.
- [x] Provide Reflex Cloud deployment configuration and instructions.
- [x] End-to-end verification (76/76 unit tests pass, zero regressions).

---

## Phase 8: Hallmark Redesign of Live Streamlit App (`hdfc_dcbm_app.py`)
- [x] Hallmark pre-flight & scope determination (Scope: App Screen, Theme: Haute Metal Champagne & Onyx)
- [x] CSS Token Architecture: Define `:root` variables, Hallmark stamp skeleton, remove `transition: all`, add instant focus-visible rings
- [x] Eliminate Floor violations: replace emoji icons with SVG/typography, eliminate tracked capitals and uppercase small caps
- [x] Tabular numerals & control density for app screen ergonomics
- [x] Preserve 100% data wiring, calculations, engine imports, and filter/export capabilities
- [x] Verification: syntax check and run full pytest test suite (76/76 passing)

---

## Phase 9: Implement Option 1 (Haute Metal Bento Executive Redesign)
- [x] Refactor Top Header Bar:
  - Eliminate the empty white box on the left (`sub_c1`)
  - Create a cohesive header: card icon, card title, `•••• 2360` badge, `Metal Edition` pill, subtitle
  - Clean action cluster on the right: secondary-style `Sync alerts` button and live status pulse pill (`09 Nov 16:56`)
- [x] Redesign Hero Bento Grid:
  - Rebalance Left Card (SmartBuy Cap Monitor): 6,840 / 10,000 RP remaining, 68.4% available, calibrated progress bar, Flights 5x and Hotels 10x headroom chips
  - Rebalance Right Card (Liquid Travel Wealth): ₹35,268 large emerald valuation, eliminate giant empty white gaps, tight 3-row metric strip (58,396 RP lifetime, 35,268 RP spendable, 5.95% net return)
  - Ensure equal height and symmetrical bento proportions
- [x] Redesign Milestones Cards:
  - Remove harsh solid underline divider bars
  - Clean 3-card layout: Welcome (Unlocked), Quarterly Bonus (10k RP Credited), Annual Fee Waiver (₹10,000 Waived)
  - Slim 5px rounded progress bars and clear achievement context
- [x] Polish Tabs & Theme CSS:
  - Replace default Streamlit red tab indicator with Champagne Gold (`#b47820`)
  - Ensure max-width container centering (1260px) for large desktop displays
- [x] Verification & Deployment:
---

## Phase 10: HSBC Live+ Dashboard Executive Redesign
- [x] Refactor CSS & Design Tokens in `HSBC Live Plus Statements/hsbc_live_plus_app.py`:
  - Set container max-width to 1260px centered
  - Define Haute Metal / HSBC executive palette (:root variables, Crimson `#db0011`, Obsidian `#0f172a`, Pearl `#f8fafc`)
  - Replace solid brown button with clean executive white button `#ffffff` + subtle border + hover
  - Tab styling without raw emojis, elegant crimson active highlight
  - Executive dark slate toast notifications
- [x] Redesign Top Header Bar:
  - Eliminate awkward floating red "H" box
  - Symmetrical header: Card switcher selectbox, `•••• 8690` badge, `Visa Infinite` pill, and subtitle
  - Right action cluster: Executive `Sync alerts` button + live pulse status pill (`friendly_time`)
- [x] Redesign Hero Section (3-Column Bento Grid):
  - Card 1: 10% Cashback Cap Monitor (`₹929.40 / ₹1,200 Cashback`, cycle countdown pill, slim 6px progress bar, confirmed + estimated split, remaining cashback)
  - Card 2: Spend Headroom (`₹2,706 spend headroom`, 10% rate pill, clean eligible merchant chips)
  - Card 3: Direct Statement Savings (`₹4,844.93 lifetime savings`, total spend tracked, and 5.98% effective reward rate)
  - Equal min-height (270px) and vertical distribution for perfect alignment
- [x] Redesign Milestones, Fee Waiver & Travel Privileges:
  - Remove harsh heavy solid colored divider bars
  - Card 1: 30-Day Welcome Benefit (`₹1,000 Cashback`, `₹20,796 spent / ₹10,000 target`, `Unlocked & Credited` pill, slim 5px progress bar)
  - Card 2: Annual Fee Waiver (`Save ₹999 + GST`, `₹81,032 / ₹200,000 spent (40.5%)`, `243D Left` pill, slim 5px progress bar, daily run-rate)
  - Card 3: Visa Infinite Privileges (`Domestic Lounge (Jul-Dec)`, `International Lounge (Annual)`, `Complimentary 1GB Global eSIM` with sleek subcard rows)
- [x] Clean Tabs & Section Titles:
  - Remove raw emoji icons from tabs and section headers (Hallmark Rule 11)
  - Modernize tab tables and perks cards
- [x] Verification & Deployment:
  - Compile with `python3 -m py_compile`
  - Pass all 76 unit tests with `pytest`
  - Restore test-touched JSON files
---

## Phase 11: Fix Visual Glitches (Equal Card Heights, Header Alignment, Progress Tracks)
- [x] Eliminate top horizontal line cut-through (`header[data-testid="stHeader"]` and `#stDecoration` display none & zero border)
- [x] Fix Header Alignment: Separate controls row from subtitle so `Sync alerts` and timestamp pill share the exact center baseline with the card switcher and badges
- [x] Enforce Equal Card Heights: Add CSS flex-stretch rules on `div[data-testid="stHorizontalBlock"]` and columns so all cards in Hero row and Milestones row have identical height and flush bottom baselines
- [x] Fix Card 1 Orphan Text Wrapping: Cleanly split confirmed/estimated and remaining cashback without orphan words
- [x] Remove all raw browser emoji glyphs (`⏳`) from countdown pills in Card 1 and Milestone 2, replacing with clean typography and status dots
- [x] Refine Progress Bars: Use elegant linear-gradient progress tracks for Card 1 (10% Cap), calibrated 5px track for Card 2 (Fee Waiver) and Card 1 (Welcome Benefit)
- [x] Verify locally with `py_compile`, run `pytest` (all 76 tests), commit and deploy to Streamlit Cloud






