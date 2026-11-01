"""Dual-Card Control Center (Modern Streamlit Version).

Unified dashboard for HDFC Diners Club Black Metal and HSBC Live+ Credit Cards.
Deployed on a separate URL from the original single-card app.
"""

import datetime
from pathlib import Path
import sys
import streamlit as st
import pandas as pd

# Path setup for engines
ROOT = Path(__file__).resolve().parent
HDFC_DIR = ROOT / "HDFC Diners Black Metal Statements"
HSBC_DIR = ROOT / "HSBC Live Plus Statements"

if str(HDFC_DIR) not in sys.path:
    sys.path.insert(0, str(HDFC_DIR))
if str(HSBC_DIR) not in sys.path:
    sys.path.insert(0, str(HSBC_DIR))

import dcbm_engine
import hsbc_engine

# Streamlit Page Config
st.set_page_config(
    page_title="Card Control Center | HDFC DCBM & HSBC Live+",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Styling
st.markdown(
    """
    <style>
    /* Card Container Styles */
    .metric-card {
        background-color: var(--background-color, #ffffff);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    .metric-title {
        font-size: 13px;
        font-weight: 600;
        color: #71717a;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 32px;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 4px;
    }
    .metric-sub {
        font-size: 12px;
        color: #a1a1aa;
    }
    .badge-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-amber { background-color: rgba(245, 158, 11, 0.15); color: #b45309; }
    .badge-green { background-color: rgba(16, 185, 129, 0.15); color: #047857; }
    .badge-red { background-color: rgba(225, 29, 72, 0.15); color: #be123c; }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_header(card_name: str, card_ending: str, badge_text: str, last_synced: str, is_hsbc: bool):
    col_brand, col_switcher, col_sync = st.columns([2.5, 2, 1.5])

    with col_brand:
        badge_cls = "badge-red" if is_hsbc else "badge-amber"
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="font-size: 28px;">💳</div>
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 20px; font-weight: 700;">{card_name}</span>
                        <span class="badge-pill {badge_cls}">•••• {card_ending}</span>
                        <span class="badge-pill {badge_cls}">{badge_text}</span>
                    </div>
                    <div style="font-size: 12px; color: #71717a;">Automated Real-Time Rewards & Spend Tracker from Gmail Alerts</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_sync:
        st.markdown(f"<div style='text-align: right; font-size: 12px; color: #10b981; font-weight: 600;'>● Synced {last_synced}</div>", unsafe_allow_html=True)


# Top Navigation / Card Selection
st.markdown("---")
switcher_col1, switcher_col2, _ = st.columns([1.5, 2, 3])
with switcher_col1:
    st.markdown("<span style='font-size: 15px; font-weight: 700;'>💳 Select Active Portfolio:</span>", unsafe_allow_html=True)
with switcher_col2:
    if hasattr(st, "segmented_control"):
        active_card = st.segmented_control(
            "Select Card",
            options=["💳 HDFC Diners Metal", "💳 HSBC Live+"],
            default="💳 HDFC Diners Metal",
            label_visibility="collapsed",
        )
    else:
        active_card = st.radio(
            "Select Card",
            options=["💳 HDFC Diners Metal", "💳 HSBC Live+"],
            horizontal=True,
            label_visibility="collapsed",
        )

# -------------------------------------------------------------
# VIEW 1: HDFC DINERS CLUB BLACK METAL
# -------------------------------------------------------------
if active_card == "💳 HDFC Diners Metal":
    data = dcbm_engine.compute_all_dashboard_data(HDFC_DIR)
    sync_meta = data.get("sync_metadata", {})
    last_synced = sync_meta.get("last_synced", "Live")
    try:
        dt = datetime.datetime.fromisoformat(last_synced)
        last_synced_str = dt.strftime("%d %b %H:%M")
    except Exception:
        last_synced_str = "Live"

    render_header("HDFC Diners Club Black Metal", "2360", "Diners Club Metal", last_synced_str, is_hsbc=False)
    st.write("")

    # Hero Bento Section
    caps = data.get("caps", {}).get("calendar_month", {})
    pts_summary = data.get("points_summary", {})
    all_txs = data.get("transactions", [])
    total_spend = sum(t.get("amount", 0.0) for t in all_txs)
    total_pts = pts_summary.get("total_estimated", 0)
    avail_pts = pts_summary.get("net_available", 0)
    ret_rate = round((total_pts / total_spend * 100), 2) if total_spend > 0 else 0.0

    b1, b2, b3 = st.columns(3)

    with b1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">ACCELERATED REWARD POINTS LIMIT</div>
                <div style="font-weight: 700; font-size: 15px; margin-bottom: 8px;">{datetime.date.today().strftime('%B %Y')} Limit</div>
                <div class="metric-value">{caps.get('earned', 0)} <span style="font-size: 18px; color: #71717a;">/ 10,000 RP</span></div>
                <div class="metric-sub">{caps.get('percent_used', 0.0):.1f}% cap utilized • Resets in {caps.get('days_remaining', 0)} days</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(1.0, float(caps.get("percent_used", 0.0)) / 100.0))

    with b2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">REMAINING SPEND HEADROOM</div>
                <div style="font-weight: 700; font-size: 15px; margin-bottom: 8px;">Spend buffer before 10k cap</div>
                <div class="metric-value">₹{caps.get('flight_spend_capacity', 75000):,}</div>
                <div class="metric-sub">✈️ 5X SmartBuy Flights Capacity (or ₹{caps.get('hotel_spend_capacity', 33300):,} for 10X Hotels)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with b3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">REWARD POINTS DETAILS</div>
                <div style="font-weight: 700; font-size: 15px; margin-bottom: 8px;">Net Balance & Portfolio Value</div>
                <div class="metric-value" style="color: #047857;">{avail_pts:,} RP</div>
                <div class="metric-sub">Lifetime Earned: {total_pts:,} RP • Realized Reward Rate: <b>{ret_rate}%</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Milestones Row
    st.write("")
    st.markdown("#### 🎯 Spend Milestones & Fee Waiver")
    milestones = data.get("milestones", {})
    m1, m2, m3 = st.columns(3)

    wel = milestones.get("welcome", {})
    with m1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="metric-title">WELCOME MILESTONE</div>
                    <span class="badge-pill badge-green">{'✅ UNLOCKED' if wel.get('met') else 'In Progress'}</span>
                </div>
                <div style="font-weight: 700; font-size: 16px;">₹1.5 Lakhs in 90 Days</div>
                <div style="font-size: 22px; font-weight: 800; margin: 4px 0;">₹{wel.get('spend', 0.0):,.0f} <span style="font-size: 14px; color: #71717a;">/ ₹1,50,000</span></div>
                <div class="metric-sub">Club Marriott, Amazon Prime & Swiggy One Claimed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(1.0, float(wel.get("progress", 0.0)) / 100.0))

    qtr = milestones.get("quarterly", {})
    with m2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="metric-title">QUARTERLY BONUS ({qtr.get('label')})</div>
                    <span class="badge-pill badge-amber">{qtr.get('days_left', 0)}d left</span>
                </div>
                <div style="font-weight: 700; font-size: 16px;">10,000 Bonus RP</div>
                <div style="font-size: 22px; font-weight: 800; margin: 4px 0;">₹{qtr.get('spend', 0.0):,.0f} <span style="font-size: 14px; color: #71717a;">/ ₹4,00,000</span></div>
                <div class="metric-sub">Remaining: ₹{qtr.get('remaining', 0.0):,.0f} (₹{qtr.get('daily_runrate_needed', 0.0):,.0f}/day)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(1.0, float(qtr.get("progress", 0.0)) / 100.0))

    ann = milestones.get("annual_waiver", {})
    with m3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="metric-title">ANNUAL FEE WAIVER</div>
                    <span class="badge-pill badge-amber">{ann.get('days_left', 0)}d left</span>
                </div>
                <div style="font-weight: 700; font-size: 16px;">Save ₹10,000 Fee</div>
                <div style="font-size: 22px; font-weight: 800; margin: 4px 0;">₹{ann.get('spend', 0.0):,.0f} <span style="font-size: 14px; color: #71717a;">/ ₹8,00,000</span></div>
                <div class="metric-sub">Remaining: ₹{ann.get('remaining', 0.0):,.0f} by {ann.get('period_end')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(1.0, float(ann.get("progress", 0.0)) / 100.0))

    # Transactions Ledger
    st.write("")
    st.markdown("#### 📜 Live Transactions Ledger")
    search_col, filter_col = st.columns([3, 1])
    with search_col:
        search_query = st.text_input("🔍 Search Merchant", placeholder="Search merchant, flight, voucher...", label_visibility="collapsed")
    with filter_col:
        category_options = ["All"] + sorted(list({t.get("category", "") for t in all_txs}))
        selected_cat = st.selectbox("Category Filter", category_options, label_visibility="collapsed")

    filtered = all_txs
    if selected_cat != "All":
        filtered = [t for t in filtered if t.get("category") == selected_cat]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered = [t for t in filtered if q in t.get("merchant", "").lower() or q in t.get("description", "").lower()]

    # Metric summary
    f_spend = sum(t.get("amount", 0.0) for t in filtered)
    f_rp = sum(t.get("total_points", 0) for t in filtered)
    st.markdown(f"**Showing {len(filtered)} transactions** • Spend: **₹{f_spend:,.2f}** • Reward Points: **{f_rp:,} RP**")

    # Table
    if filtered:
        df = pd.DataFrame(
            [
                {
                    "Date": t.get("date"),
                    "Merchant": t.get("merchant"),
                    "Category": t.get("category"),
                    "Amount (₹)": f"₹{t.get('amount', 0.0):,.2f}",
                    "Base RP": t.get("base_points", 0),
                    "Accelerated RP": t.get("raw_accelerated_points", 0),
                    "Total RP": t.get("total_points", 0),
                    "Multiplier": f"{t.get('total_multiplier', 1)}X",
                }
                for t in filtered
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions match the selected filters.")

# -------------------------------------------------------------
# VIEW 2: HSBC LIVE+ CREDIT CARD
# -------------------------------------------------------------
else:
    data = hsbc_engine.compute_hsbc_dashboard_data(HSBC_DIR)
    sync_meta = data.get("sync_metadata", {})
    last_synced = sync_meta.get("last_synced", "Live")
    try:
        dt = datetime.datetime.fromisoformat(last_synced)
        last_synced_str = dt.strftime("%d %b %H:%M")
    except Exception:
        last_synced_str = "Live"

    render_header("HSBC Live+ Credit Card", "8690", "Visa Platinum", last_synced_str, is_hsbc=True)
    st.write("")

    # Hero Bento Section
    cap = data.get("cashback_cap", {})
    pf = data.get("portfolio", {})
    cycle = data.get("cycle", {})

    b1, b2, b3 = st.columns(3)

    with b1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">MONTHLY ACCELERATED CASHBACK CAP</div>
                <div style="font-weight: 700; font-size: 15px; margin-bottom: 8px;">{cycle.get('label', 'Current Cycle')}</div>
                <div class="metric-value">₹{cap.get('earned', 0.0):,.2f} <span style="font-size: 18px; color: #71717a;">/ ₹1,200</span></div>
                <div class="metric-sub">{cap.get('percent_used', 0.0):.1f}% utilized • Remaining Cap: <b>₹{cap.get('remaining_cb', 0.0):,.2f}</b> • {cycle.get('reset_str')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(1.0, float(cap.get("percent_used", 0.0)) / 100.0))

    with b2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">10% CASHBACK SPEND HEADROOM</div>
                <div style="font-weight: 700; font-size: 15px; margin-bottom: 8px;">Dining, Food Delivery & Grocery</div>
                <div class="metric-value">₹{cap.get('remaining_accelerated_spend', 0.0):,.0f}</div>
                <div class="metric-sub">Spent ₹{cap.get('accelerated_spend', 0.0):,.0f} of ₹12,000 threshold. Spends beyond earn 1.5% unlimited base cashback.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with b3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">LIFETIME DIRECT CASHBACK</div>
                <div style="font-weight: 700; font-size: 15px; margin-bottom: 8px;">Direct Statement Credits</div>
                <div class="metric-value" style="color: #047857;">₹{pf.get('lifetime_cashback', 0.0):,.2f}</div>
                <div class="metric-sub">Total Spend: ₹{pf.get('lifetime_spend', 0.0):,.0f} • Effective Reward Rate: <b>{pf.get('effective_reward_rate', 0.0):.2f}% Return</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Milestones Row
    st.write("")
    st.markdown("#### 🎯 Milestones & Lifestyle Privileges")
    wel = data.get("welcome", {})
    fw = data.get("fee_waiver", {})
    lg = data.get("lounge", {})

    m1, m2, m3 = st.columns(3)

    with m1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="metric-title">WELCOME MILESTONE</div>
                    <span class="badge-pill badge-green">{'✅ UNLOCKED' if wel.get('unlocked') else 'In Progress'}</span>
                </div>
                <div style="font-weight: 700; font-size: 16px;">₹20,000 Spend in 30 Days</div>
                <div style="font-size: 22px; font-weight: 800; margin: 4px 0;">₹{wel.get('spent', 0.0):,.0f} <span style="font-size: 14px; color: #71717a;">/ ₹20,000</span></div>
                <div class="metric-sub">₹1,000 Amazon Voucher Claimed & Processed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(1.0)

    with m2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="metric-title">ANNUAL FEE WAIVER</div>
                    <span class="badge-pill badge-red">{fw.get('days_left', 0)}d left</span>
                </div>
                <div style="font-weight: 700; font-size: 16px;">Save ₹999 + GST</div>
                <div style="font-size: 22px; font-weight: 800; margin: 4px 0;">₹{fw.get('spent', 0.0):,.0f} <span style="font-size: 14px; color: #71717a;">/ ₹2,00,000</span></div>
                <div class="metric-sub">Remaining: ₹{fw.get('remaining', 0.0):,.0f} ({fw.get('percent', 0.0):.1f}% completed)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(1.0, float(fw.get("percent", 0.0)) / 100.0))

    with m3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="metric-title">TRAVEL & LIFESTYLE</div>
                    <span class="badge-pill badge-green">Complimentary</span>
                </div>
                <div style="font-weight: 700; font-size: 16px;">Lounges & Roaming</div>
                <div style="margin: 8px 0; font-size: 13px;">
                    <div>✈️ Domestic Lounge (H2): <b>{lg.get('domestic_h2')}</b></div>
                    <div>🌍 International Lounge: <b>{lg.get('international')}</b></div>
                    <div>📶 International eSIM: <b>{lg.get('esim')}</b></div>
                </div>
                <div class="metric-sub">🍽️ 15% Dining Privileges across partner restaurants</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # HSBC Transactions Ledger
    st.write("")
    st.markdown("#### 📜 HSBC Live+ Transactions Ledger")
    hsbc_txs = data.get("transactions", {}).get("all", [])

    search_col, filter_col = st.columns([3, 1])
    with search_col:
        search_query = st.text_input("🔍 Search Merchant", placeholder="Search Swiggy, Blinkit, Royal Mart, MCC...", label_visibility="collapsed")
    with filter_col:
        category_options = ["All"] + sorted(list({t.get("category", "") for t in hsbc_txs}))
        selected_cat = st.selectbox("Category Filter", category_options, label_visibility="collapsed")

    filtered = hsbc_txs
    if selected_cat != "All":
        filtered = [t for t in filtered if t.get("category") == selected_cat]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered = [t for t in filtered if q in t.get("merchant", "").lower() or q in t.get("mcc", "").lower()]

    f_spend = sum(t.get("amount", 0.0) for t in filtered)
    f_cb = sum(t.get("cashback_earned", 0.0) for t in filtered)
    st.markdown(f"**Showing {len(filtered)} transactions** • Spend: **₹{f_spend:,.2f}** • Cashback: **+₹{f_cb:,.2f}**")

    if filtered:
        df = pd.DataFrame(
            [
                {
                    "Date": t.get("date"),
                    "Merchant": t.get("merchant"),
                    "Category": t.get("category"),
                    "Amount (₹)": f"₹{t.get('amount', 0.0):,.2f}",
                    "MCC": t.get("mcc", "N/A"),
                    "Rate": t.get("rate"),
                    "Cashback": f"+₹{t.get('cashback_earned', 0.0):,.2f}",
                    "Status": t.get("evidence", "confirmed"),
                }
                for t in filtered
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions match the selected filters.")
