"""Reflex State for the HDFC Diners Club Black Metal Control Center."""

import datetime
from pathlib import Path
import sys
from typing import List

from pydantic import BaseModel
import reflex as rx

# Locate HDFC Diners Black Metal Statements directory (Local vs Cloud fallback)
ROOT_CARD_DIR = Path(__file__).resolve().parent.parent.parent / "HDFC Diners Black Metal Statements"
LOCAL_DATA_DIR = Path(__file__).resolve().parent / "data"

if ROOT_CARD_DIR.exists() and (ROOT_CARD_DIR / "gmail_alerts.json").exists():
    CARD_DIR = ROOT_CARD_DIR
else:
    CARD_DIR = LOCAL_DATA_DIR

if str(ROOT_CARD_DIR) not in sys.path and ROOT_CARD_DIR.exists():
    sys.path.insert(0, str(ROOT_CARD_DIR))
LOCAL_DIR = Path(__file__).resolve().parent
if str(LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_DIR))

# Locate HSBC Live Plus Statements directory (Local vs Cloud fallback)
ROOT_HSBC_DIR = Path(__file__).resolve().parent.parent.parent / "HSBC Live Plus Statements"
LOCAL_HSBC_DIR = Path(__file__).resolve().parent / "hsbc_data"

if ROOT_HSBC_DIR.exists() and (ROOT_HSBC_DIR / "gmail_alerts.json").exists():
    HSBC_DIR = ROOT_HSBC_DIR
else:
    HSBC_DIR = LOCAL_HSBC_DIR

if str(ROOT_HSBC_DIR) not in sys.path and ROOT_HSBC_DIR.exists():
    sys.path.insert(0, str(ROOT_HSBC_DIR))

try:
    import dcbm_engine
except ImportError:
    from dcbm_reflex import dcbm_engine

try:
    import hsbc_engine
except ImportError:
    from dcbm_reflex import hsbc_engine


def get_hsbc_icon(cat: str) -> str:
    if "Dining" in cat or "food" in cat.lower():
        return "🍽️"
    if "Grocery" in cat:
        return "🛒"
    if "Travel" in cat:
        return "✈️"
    if "Shopping" in cat:
        return "🛍️"
    if "Lounge" in cat:
        return "💳"
    return "⚡"


class HSBCTxItem(BaseModel):
    date: str
    merchant: str
    category: str
    icon: str
    amount: float
    formatted_amount: str
    mcc: str
    rate: str
    is_accelerated: bool
    cashback_earned: float
    formatted_cashback: str
    evidence: str
    source: str
    is_token: bool


class TxItem(BaseModel):

    message_id: str
    date: str
    merchant: str
    category: str
    icon: str
    amount: float
    formatted_amount: str
    base_points: int
    raw_accelerated_points: int
    total_points: int
    reward_rate: float
    is_smartbuy: bool
    multiplier: int
    description: str


class MonthHistoryItem(BaseModel):
    label: str
    month_name: str
    year: int
    month: int
    total_spend: float
    formatted_spend: str
    base_points: int
    accelerated_points: int
    total_points: int
    cap_percent_used: int
    cap_percent_used_float: float
    accelerated_remaining: int
    realized_value_inr: float
    formatted_value: str
    smartbuy_txs: str


class RedemptionItem(BaseModel):
    date: str
    type: str
    description: str
    order_reference: str
    points_redeemed: int
    cash_paid: float
    formatted_cash: str
    total_fare: float
    formatted_fare: str
    value_saved_inr: float
    formatted_saved: str
    redemption_rate: float


class DCBMState(rx.State):
    """Central reactive state for DCBM and HSBC Control Centers."""

    # Active Card Selection ("HDFC" or "HSBC")
    active_card: str = "HDFC"

    # Top Bar & Metadata - HDFC Diners Black Metal
    card_name: str = "HDFC Diners Club Black Metal"
    card_ending: str = "•••• 2360"
    last_synced: str = "Live"
    is_syncing: bool = False

    # Top Bar & Metadata - HSBC Live+
    hsbc_card_name: str = "HSBC Live+ Credit Card"
    hsbc_card_ending: str = "•••• 8690"
    hsbc_last_synced: str = "Live"
    hsbc_is_syncing: bool = False

    # HSBC Cycle & Cashback Cap
    hsbc_cycle_label: str = "Current Cycle (14 Oct – 13 Nov)"
    hsbc_days_remaining: int = 12
    hsbc_reset_str: str = "Resets in 12 days"
    hsbc_cap_limit: float = 1200.0
    hsbc_cap_earned: float = 718.8
    hsbc_cap_remaining: float = 481.2
    hsbc_cap_percent_used: int = 60
    hsbc_cap_percent_used_float: float = 59.9
    hsbc_total_cycle_cb: float = 738.22
    hsbc_formatted_cap_earned: str = "₹718.80"
    hsbc_formatted_cap_remaining: str = "₹481.20"
    hsbc_formatted_total_cb: str = "₹738.22"

    # HSBC Spend Headroom (10% on Dining/Food Delivery/Grocery)
    hsbc_accelerated_spend: float = 7188.0
    hsbc_max_accelerated_spend: float = 12000.0
    hsbc_remaining_accelerated_spend: float = 4812.0
    hsbc_formatted_remaining_spend: str = "₹4,812"
    hsbc_formatted_spent: str = "₹7,188"

    # HSBC Portfolio & Realized Reward Rate
    hsbc_lifetime_cashback: float = 4634.33
    hsbc_formatted_lifetime_cb: str = "₹4,634.33"
    hsbc_lifetime_spend: float = 78926.29
    hsbc_formatted_lifetime_spend: str = "₹78,926"
    hsbc_effective_reward_rate: float = 5.87

    # HSBC Milestones: Fee Waiver (₹2,00,000 spend)
    hsbc_fee_target: float = 200000.0
    hsbc_fee_spent: float = 78926.29
    hsbc_fee_remaining: float = 121073.71
    hsbc_formatted_fee_remaining: str = "₹1,21,074"
    hsbc_fee_percent: int = 40
    hsbc_fee_percent_float: float = 39.5
    hsbc_fee_days_left: int = 239
    hsbc_fee_run_rate: float = 506.58

    # HSBC Milestones: Welcome Milestone (₹20k spend / 30d)
    hsbc_welcome_spent: float = 20796.46
    hsbc_welcome_target: float = 20000.0
    hsbc_welcome_unlocked: bool = True
    hsbc_welcome_reward: int = 1000
    hsbc_welcome_progress: int = 100

    # HSBC Airport Lounge & Perks
    hsbc_lounge_domestic: str = "1 Visit Left"
    hsbc_lounge_international: str = "1 Visit Left"
    hsbc_lounge_esim: str = "Active"

    # HSBC Collections & Controls
    hsbc_transactions: List[HSBCTxItem] = []
    hsbc_categories: List[str] = ["All"]
    hsbc_selected_category: str = "All"
    hsbc_selected_period: str = "All Transactions"
    hsbc_period_options: List[str] = [
        "All Transactions",
        "Current Cycle Only",
        "10% Accelerated Dining & Grocery Only",
    ]
    hsbc_search_query: str = ""


    # Section 1: Hero Cap Monitor
    cycle_title: str = "Limit"
    days_remaining: int = 0
    reset_date: str = ""
    monthly_cap: int = 10000
    cap_earned: int = 0
    cap_remaining: int = 10000
    cap_percent_used: int = 0
    cap_percent_remaining: float = 100.0
    today_earned: int = 0
    today_cap: int = 2500

    # Headroom
    flight_spend_capacity: int = 75000
    formatted_flight_capacity: str = "₹75,000"
    hotel_spend_capacity: int = 33300
    formatted_hotel_capacity: str = "₹33,300"

    # Portfolio
    lifetime_earned: int = 0
    current_available: int = 0
    total_spend_all: float = 0.0
    lifetime_reward_rate: float = 0.0

    # Milestones
    welcome_spend: float = 0.0
    welcome_target: float = 150000.0
    welcome_progress: int = 0
    welcome_met: bool = False
    welcome_days_left: int = 0

    q_label: str = "Quarterly Bonus"
    q_spend: float = 0.0
    q_target: float = 400000.0
    q_progress: int = 0
    q_met: bool = False
    q_days_left: int = 0
    q_remaining: float = 0.0
    q_runrate: float = 0.0

    ann_spend: float = 0.0
    ann_target: float = 800000.0
    ann_progress: int = 0
    ann_met: bool = False
    ann_days_left: int = 0
    ann_remaining: float = 0.0
    ann_deadline: str = ""

    # Redemptions summary
    total_pts_burned: int = 0
    total_direct_savings: float = 0.0
    formatted_savings: str = "₹0"
    total_booking_val: float = 0.0
    formatted_booking_val: str = "₹0"
    total_cash_paid: float = 0.0
    formatted_cash_paid: str = "₹0"

    # Raw Data Collections
    transactions: List[TxItem] = []
    monthly_history: List[MonthHistoryItem] = []
    redemptions: List[RedemptionItem] = []
    categories: List[str] = ["All"]
    period_options: List[str] = ["All Transactions", "SmartBuy Accelerated Only"]

    # Interactive UI Controls
    selected_category: str = "All"
    selected_period: str = "All Transactions"
    search_query: str = ""
    active_tab: str = "transactions"

    def load_data(self):
        """Compute and load all data from dcbm_engine."""
        try:
            data = dcbm_engine.compute_all_dashboard_data(CARD_DIR)
        except Exception as e:
            print(f"Error computing data from engine: {e}")
            return

        # Top Bar
        sync_meta = data.get("sync_metadata", {})
        ts_str = sync_meta.get("last_synced", "")
        try:
            dt = datetime.datetime.fromisoformat(ts_str)
            self.last_synced = dt.strftime("%d %b %H:%M")
        except Exception:
            self.last_synced = "Live"

        # Cap Monitor
        active_cap = data.get("caps", {}).get("calendar_month", {})
        now = datetime.date.today()
        self.cycle_title = f"{now.strftime('%B %Y')} Limit"
        self.days_remaining = int(active_cap.get("days_remaining", 0))
        self.reset_date = str(active_cap.get("reset_date", ""))
        self.monthly_cap = int(active_cap.get("monthly_cap", 10000))
        self.cap_earned = int(active_cap.get("earned", 0))
        self.cap_remaining = int(active_cap.get("remaining", 10000))
        self.cap_percent_used = int(round(float(active_cap.get("percent_used", 0.0))))
        self.cap_percent_remaining = float(active_cap.get("percent_remaining", 100.0))
        self.today_earned = int(active_cap.get("today_earned", 0))
        self.today_cap = int(active_cap.get("daily_cap", 2500))

        # Headroom
        self.flight_spend_capacity = int(active_cap.get("flight_spend_capacity", 75000))
        self.formatted_flight_capacity = f"₹{self.flight_spend_capacity:,}"
        self.hotel_spend_capacity = int(active_cap.get("hotel_spend_capacity", 33300))
        self.formatted_hotel_capacity = f"₹{self.hotel_spend_capacity:,}"

        # Portfolio Metrics
        pts_summary = data.get("points_summary", {})
        self.lifetime_earned = int(pts_summary.get("total_estimated", 0))
        self.current_available = int(pts_summary.get("net_available", 0))
        raw_txs = data.get("transactions", [])
        self.total_spend_all = float(sum(t.get("amount", 0.0) for t in raw_txs))
        self.lifetime_reward_rate = (
            round((self.lifetime_earned / self.total_spend_all * 100), 2)
            if self.total_spend_all > 0
            else 0.0
        )

        # Milestones
        milestones = data.get("milestones", {})
        welcome = milestones.get("welcome", {})
        self.welcome_spend = float(welcome.get("spend", 0.0))
        self.welcome_target = float(welcome.get("target", 150000.0))
        self.welcome_progress = int(round(min(100.0, float(welcome.get("progress", 0.0)))))
        self.welcome_met = bool(welcome.get("met", False))
        self.welcome_days_left = int(welcome.get("days_left", 0))

        quarterly = milestones.get("quarterly", {})
        self.q_label = f"Quarterly Bonus ({quarterly.get('label', 'Current')})"
        self.q_spend = float(quarterly.get("spend", 0.0))
        self.q_target = float(quarterly.get("target", 400000.0))
        self.q_progress = int(round(min(100.0, float(quarterly.get("progress", 0.0)))))
        self.q_met = bool(quarterly.get("met", False))
        self.q_days_left = int(quarterly.get("days_left", 0))
        self.q_remaining = float(quarterly.get("remaining", 0.0))
        self.q_runrate = float(quarterly.get("daily_runrate_needed", 0.0))

        annual = milestones.get("annual_waiver", {})
        self.ann_spend = float(annual.get("spend", 0.0))
        self.ann_target = float(annual.get("target", 800000.0))
        self.ann_progress = int(round(min(100.0, float(annual.get("progress", 0.0)))))
        self.ann_met = bool(annual.get("met", False))
        self.ann_days_left = int(annual.get("days_left", 0))
        self.ann_remaining = float(annual.get("remaining", 0.0))
        self.ann_deadline = str(annual.get("period_end", ""))

        # Transactions
        tx_list = []
        for t in raw_txs:
            base = int(t.get("base_points", 0))
            acc = int(t.get("raw_accelerated_points", 0))
            mult = int(t.get("total_multiplier", 1))
            amt = float(t.get("amount", 0.0))
            tx_list.append(
                TxItem(
                    message_id=str(t.get("message_id", "")),
                    date=str(t.get("date", "")),
                    merchant=str(t.get("merchant", "")),
                    category=str(t.get("category", "General Retail")),
                    icon=str(t.get("icon", "🛍️")),
                    amount=amt,
                    formatted_amount=f"₹{amt:,.2f}",
                    base_points=base,
                    raw_accelerated_points=acc,
                    total_points=base + acc,
                    reward_rate=round(mult * 3.33, 1),
                    is_smartbuy=bool(t.get("is_smartbuy", False)),
                    multiplier=mult,
                    description=str(t.get("description", "")),
                )
            )
        self.transactions = tx_list

        # Categories list
        cats = sorted(list({t.category for t in tx_list}))
        self.categories = ["All"] + cats

        # Monthly History
        hist_list = []
        history_raw = data.get("monthly_history", [])
        period_opts = ["All Transactions", "SmartBuy Accelerated Only"]
        for h in history_raw:
            sp = float(h.get("total_spend", 0.0))
            hist_list.append(
                MonthHistoryItem(
                    label=str(h.get("label", "")),
                    month_name=str(h.get("month_name", "")),
                    year=int(h.get("year", 2026)),
                    month=int(h.get("month", 1)),
                    total_spend=sp,
                    formatted_spend=f"₹{sp:,.0f}",
                    base_points=int(h.get("base_points", 0)),
                    accelerated_points=int(h.get("accelerated_points", 0)),
                    total_points=int(h.get("total_points", 0)),
                    cap_percent_used=int(round(min(100.0, float(h.get("accelerated_percent_used", 0.0))))),
                    cap_percent_used_float=round(float(h.get("accelerated_percent_used", 0.0)), 1),
                    accelerated_remaining=int(h.get("accelerated_remaining", 0)),
                    realized_value_inr=float(h.get("realized_value_inr", 0.0)),
                    formatted_value=f"₹{h.get('realized_value_inr', 0.0):,.0f}",
                    smartbuy_txs=f"{h.get('smartbuy_tx_count', 0)} / {h.get('total_tx_count', 0)}",
                )
            )
            period_opts.append(f"Month: {h.get('label')}")
        self.monthly_history = hist_list
        self.period_options = period_opts

        # Redemptions
        red_list = []
        raw_reds = data.get("redemptions", [])
        for r in raw_reds:
            pts = int(r.get("points_redeemed", 0))
            cash = float(r.get("cash_paid", 0.0))
            fare = float(r.get("total_fare", 0.0))
            saved = float(r.get("value_saved_inr", 0.0))
            rate = float(r.get("redemption_rate", 1.0))
            red_list.append(
                RedemptionItem(
                    date=str(r.get("date", "")),
                    type=str(r.get("type", "SmartBuy Flight")),
                    description=str(r.get("description", "")),
                    order_reference=str(r.get("order_reference", "")),
                    points_redeemed=pts,
                    cash_paid=cash,
                    formatted_cash=f"₹{cash:,.0f}",
                    total_fare=fare,
                    formatted_fare=f"₹{fare:,.0f}",
                    value_saved_inr=saved,
                    formatted_saved=f"₹{saved:,.0f}",
                    redemption_rate=rate,
                )
            )
        self.redemptions = red_list

        self.total_pts_burned = sum(r.points_redeemed for r in red_list)
        self.total_direct_savings = sum(r.value_saved_inr for r in red_list)
        self.formatted_savings = f"₹{self.total_direct_savings:,.0f}"
        self.total_booking_val = sum(r.total_fare for r in red_list)
        self.formatted_booking_val = f"₹{self.total_booking_val:,.0f}"
        self.total_cash_paid = sum(r.cash_paid for r in red_list)
        self.formatted_cash_paid = f"₹{self.total_cash_paid:,.0f}"

        # Load HSBC data simultaneously
        self.load_hsbc_data()

    def load_hsbc_data(self):
        """Compute and load all HSBC Live+ data from hsbc_engine."""
        try:
            data = hsbc_engine.compute_hsbc_dashboard_data(HSBC_DIR)
        except Exception as e:
            print(f"Error computing HSBC data: {e}")
            return

        sync_meta = data.get("sync_metadata", {})
        ts_str = sync_meta.get("last_synced", "")
        try:
            dt = datetime.datetime.fromisoformat(ts_str)
            self.hsbc_last_synced = dt.strftime("%d %b %H:%M")
        except Exception:
            self.hsbc_last_synced = "Live"

        cycle = data.get("cycle", {})
        self.hsbc_cycle_label = str(cycle.get("label", "Current Cycle"))
        self.hsbc_days_remaining = int(cycle.get("days_remaining", 0))
        self.hsbc_reset_str = str(cycle.get("reset_str", ""))

        cap = data.get("cashback_cap", {})
        self.hsbc_cap_limit = float(cap.get("cap_limit", 1200.0))
        self.hsbc_cap_earned = float(cap.get("earned", 0.0))
        self.hsbc_cap_remaining = float(cap.get("remaining_cb", 0.0))
        pct = float(cap.get("percent_used", 0.0))
        self.hsbc_cap_percent_used = int(round(min(100.0, pct)))
        self.hsbc_cap_percent_used_float = round(pct, 1)
        self.hsbc_total_cycle_cb = float(cap.get("total_cycle_cb", 0.0))
        self.hsbc_formatted_cap_earned = f"₹{self.hsbc_cap_earned:,.2f}"
        self.hsbc_formatted_cap_remaining = f"₹{self.hsbc_cap_remaining:,.2f}"
        self.hsbc_formatted_total_cb = f"₹{self.hsbc_total_cycle_cb:,.2f}"

        self.hsbc_accelerated_spend = float(cap.get("accelerated_spend", 0.0))
        self.hsbc_max_accelerated_spend = float(cap.get("max_accelerated_spend", 12000.0))
        self.hsbc_remaining_accelerated_spend = float(cap.get("remaining_accelerated_spend", 0.0))
        self.hsbc_formatted_remaining_spend = f"₹{self.hsbc_remaining_accelerated_spend:,.0f}"
        self.hsbc_formatted_spent = f"₹{self.hsbc_accelerated_spend:,.0f}"

        pf = data.get("portfolio", {})
        self.hsbc_lifetime_cashback = float(pf.get("lifetime_cashback", 0.0))
        self.hsbc_formatted_lifetime_cb = f"₹{self.hsbc_lifetime_cashback:,.2f}"
        self.hsbc_lifetime_spend = float(pf.get("lifetime_spend", 0.0))
        self.hsbc_formatted_lifetime_spend = f"₹{self.hsbc_lifetime_spend:,.0f}"
        self.hsbc_effective_reward_rate = float(pf.get("effective_reward_rate", 0.0))

        fw = data.get("fee_waiver", {})
        self.hsbc_fee_target = float(fw.get("target", 200000.0))
        self.hsbc_fee_spent = float(fw.get("spent", 0.0))
        self.hsbc_fee_remaining = float(fw.get("remaining", 0.0))
        self.hsbc_formatted_fee_remaining = f"₹{self.hsbc_fee_remaining:,.0f}"
        fw_pct = float(fw.get("percent", 0.0))
        self.hsbc_fee_percent = int(round(min(100.0, fw_pct)))
        self.hsbc_fee_percent_float = round(fw_pct, 1)
        self.hsbc_fee_days_left = int(fw.get("days_left", 0))
        self.hsbc_fee_run_rate = float(fw.get("run_rate_needed", 0.0))

        wm = data.get("welcome", {})
        self.hsbc_welcome_spent = float(wm.get("spent", 0.0))
        self.hsbc_welcome_target = float(wm.get("target", 20000.0))
        self.hsbc_welcome_unlocked = bool(wm.get("unlocked", False))
        self.hsbc_welcome_reward = int(wm.get("reward", 1000))
        self.hsbc_welcome_progress = 100 if self.hsbc_welcome_unlocked else int(round((self.hsbc_welcome_spent / self.hsbc_welcome_target) * 100))

        lg = data.get("lounge", {})
        self.hsbc_lounge_domestic = str(lg.get("domestic_h2", "1 Visit Left"))
        self.hsbc_lounge_international = str(lg.get("international", "1 Visit Left"))
        self.hsbc_lounge_esim = str(lg.get("esim", "Active"))

        # Transactions
        raw_hsbc_txs = data.get("transactions", {}).get("all", [])
        tx_items = []
        for t in raw_hsbc_txs:
            amt = float(t.get("amount", 0.0))
            cb = float(t.get("cashback_earned", 0.0))
            cat = str(t.get("category", "Other Eligible Spends"))
            tx_items.append(
                HSBCTxItem(
                    date=str(t.get("date", "")),
                    merchant=str(t.get("merchant", "")),
                    category=cat,
                    icon=get_hsbc_icon(cat),
                    amount=amt,
                    formatted_amount=f"₹{amt:,.2f}",
                    mcc=str(t.get("mcc", "N/A")),
                    rate=str(t.get("rate", "1.5%")),
                    is_accelerated=bool(t.get("is_accelerated", False)),
                    cashback_earned=cb,
                    formatted_cashback=f"+₹{cb:,.2f}",
                    evidence=str(t.get("evidence", "")),
                    source=str(t.get("source", "")),
                    is_token=bool(t.get("is_token", False)),
                )
            )
        self.hsbc_transactions = tx_items

        cats = sorted(list({t.category for t in tx_items}))
        self.hsbc_categories = ["All"] + cats

    @rx.var
    def filtered_transactions(self) -> List[TxItem]:
        """Compute filtered list of transactions reactively."""
        res = self.transactions

        # Filter by period
        if self.selected_period == "SmartBuy Accelerated Only":
            res = [t for t in res if t.is_smartbuy]
        elif self.selected_period.startswith("Month: "):
            m_label = self.selected_period.replace("Month: ", "").strip()
            # Match year-month from history
            m_match = next((h for h in self.monthly_history if h.label == m_label), None)
            if m_match:
                prefix = f"{m_match.year}-{m_match.month:02d}"
                res = [t for t in res if t.date.startswith(prefix)]

        # Filter by category
        if self.selected_category != "All":
            res = [t for t in res if t.category == self.selected_category]

        # Search query
        if self.search_query.strip():
            q = self.search_query.strip().lower()
            res = [t for t in res if q in t.merchant.lower() or q in t.description.lower()]

        return res

    @rx.var
    def filtered_count(self) -> int:
        return len(self.filtered_transactions)

    @rx.var
    def filtered_spend_formatted(self) -> str:
        tot = sum(t.amount for t in self.filtered_transactions)
        return f"₹{tot:,.2f}"

    @rx.var
    def filtered_base_rp(self) -> int:
        return sum(t.base_points for t in self.filtered_transactions)

    @rx.var
    def filtered_acc_rp(self) -> int:
        return sum(t.raw_accelerated_points for t in self.filtered_transactions)

    @rx.var
    def filtered_total_rp(self) -> int:
        return sum(t.total_points for t in self.filtered_transactions)

    # HSBC Reactive Computations
    @rx.var
    def hsbc_filtered_transactions(self) -> List[HSBCTxItem]:
        res = self.hsbc_transactions
        if self.hsbc_selected_period == "Current Cycle Only":
            # Current statement cycle runs from 14 Oct 2026 onwards
            res = [t for t in res if t.date >= "2026-10-14"]
        elif self.hsbc_selected_period == "10% Accelerated Dining & Grocery Only":
            res = [t for t in res if t.is_accelerated]

        if self.hsbc_selected_category != "All":
            res = [t for t in res if t.category == self.hsbc_selected_category]

        if self.hsbc_search_query.strip():
            q = self.hsbc_search_query.strip().lower()
            res = [t for t in res if q in t.merchant.lower() or q in t.category.lower() or q in t.mcc.lower()]

        return res

    @rx.var
    def hsbc_filtered_count(self) -> int:
        return len(self.hsbc_filtered_transactions)

    @rx.var
    def hsbc_filtered_spend_formatted(self) -> str:
        tot = sum(t.amount for t in self.hsbc_filtered_transactions)
        return f"₹{tot:,.2f}"

    @rx.var
    def hsbc_filtered_cashback_formatted(self) -> str:
        tot = sum(t.cashback_earned for t in self.hsbc_filtered_transactions)
        return f"+₹{tot:,.2f}"

    def set_active_card(self, card: str | list[str]):
        if isinstance(card, list):
            self.active_card = card[0] if card else "HDFC"
        else:
            self.active_card = card

    def set_search_query(self, query: str):
        self.search_query = query

    def set_category(self, cat: str):
        self.selected_category = cat

    def set_period(self, per: str):
        self.selected_period = per

    def set_tab(self, tab_id: str):
        self.active_tab = tab_id

    def set_hsbc_search_query(self, query: str):
        self.hsbc_search_query = query

    def set_hsbc_category(self, cat: str):
        self.hsbc_selected_category = cat

    def set_hsbc_period(self, per: str):
        self.hsbc_selected_period = per

    async def trigger_sync(self):
        """Trigger live Gmail sync in background for HDFC Diners Metal."""
        self.is_syncing = True
        yield
        try:
            sync_res = dcbm_engine.trigger_live_sync(CARD_DIR)
            self.load_data()
            count = sync_res.get("alert_count", 0)
            yield rx.toast.success(f"Synced {count} alerts for HDFC Diners Metal!", position="top-right")
        except Exception as exc:
            yield rx.toast.error(f"Sync error: {exc}", position="top-right")
        finally:
            self.is_syncing = False

    async def trigger_hsbc_sync(self):
        """Trigger live Gmail sync in background for HSBC Live+."""
        self.hsbc_is_syncing = True
        yield
        try:
            sync_res = hsbc_engine.trigger_live_sync(HSBC_DIR)
            self.load_hsbc_data()
            count = sync_res.get("alert_count", 0)
            yield rx.toast.success(f"Synced {count} alerts for HSBC Live+!", position="top-right")
        except Exception as exc:
            yield rx.toast.error(f"HSBC sync error: {exc}", position="top-right")
        finally:
            self.hsbc_is_syncing = False

    async def trigger_current_sync(self):
        """Trigger sync for whichever card is currently active."""
        if self.active_card == "HSBC":
            async for item in self.trigger_hsbc_sync():
                yield item
        else:
            async for item in self.trigger_sync():
                yield item

