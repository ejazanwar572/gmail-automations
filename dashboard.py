import os
import json
import sqlite3
import datetime
import subprocess
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from tracker_config import DB_PATH, SETTINGS_PATH

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Orange Ledger",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Global Styles (via st.html — bypasses markdown parser) ──────────────────
st.html("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
    .stApp {
        background-color: #0b0f19 !important;
        color: #f1f5f9 !important;
    }
    html, body, [class*="css"], .stMarkdown, p, div, label, span, h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
    }

    /* Collapse Streamlit header to zero height — removes dead space at top */
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    #stDecoration { display: none !important; }
    header[data-testid="stHeader"] {
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        background-color: #0b0f19 !important;
        border-bottom: none !important;
        overflow: hidden !important;
    }
    /* Remove default top padding from main block that accounts for header */
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 20px !important;
    }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #0b0f19; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #FC8019; }

    .metric-card-wrapper {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 20px 24px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.15);
        margin-bottom: 15px;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        gap: 4px;
    }
    .metric-card-wrapper:hover {
        transform: translateY(-2px);
        border-color: #FC8019;
        box-shadow: 0 10px 20px -3px rgb(0 0 0 / 0.3), 0 0 12px rgba(252,128,25,0.25);
    }
    .metric-title {
        color: #94a3b8;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
    }
    .metric-value-text {
        color: #ffffff;
        font-size: 26px;
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }
    .metric-sub {
        color: #64748b;
        font-size: 12px;
        font-weight: 500;
        margin-top: 2px;
    }
    .metric-delta { font-size: 13px; margin-top: 4px; font-weight: 600; }
    .delta-positive { color: #f87171; }
    .delta-negative { color: #4ade80; }

    div.stButton > button, div.stDownloadButton > button {
        background-color: #FC8019 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 8px 18px !important;
        transition: background-color 0.2s ease, transform 0.1s ease !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: #e5730d !important;
        transform: translateY(-1px);
    }
    div.stButton > button:active, div.stDownloadButton > button:active {
        transform: translateY(1px);
    }

    [data-testid="stSidebar"] {
        background-color: #05070c !important;
        border-right: 1px solid #1e293b;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 { color: #ffffff !important; }

    div[data-testid="stAlert"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
    }
    div[data-testid="stAlert"] p { color: #cbd5e1 !important; }

    .stTextInput input, div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    [data-baseweb="select"] [data-baseweb="select"],
    div[data-testid="stSelectbox"] > div {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    input:focus, div[data-baseweb="select"]:focus-within {
        border-color: #FC8019 !important;
        box-shadow: 0 0 0 2px rgba(252,128,25,0.2) !important;
    }
    /* Dark number inputs */
    input[type="number"] {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    /* Selectbox dropdown menu */
    ul[data-baseweb="menu"], [data-baseweb="popover"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
    }
    li[role="option"] {
        color: #f1f5f9 !important;
    }
    li[role="option"]:hover {
        background-color: rgba(252,128,25,0.15) !important;
        color: #FC8019 !important;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 15px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 600;
        color: #94a3b8 !important;
        background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab"]:hover { color: #FC8019 !important; }
    .stTabs [aria-selected="true"] {
        color: #FC8019 !important;
        border-bottom: 2px solid #FC8019 !important;
    }

    .timeline-selector-label {
        font-size: 13px;
        font-weight: 700;
        color: #FC8019;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }

    .section-divider {
        border: none;
        border-top: 1px solid #1e293b;
        margin: 28px 0;
    }
    </style>
""")

# ─── Dark Plotly theme helper ─────────────────────────────────────────────────
PLOTLY_DARK = dict(
    plot_bgcolor="#1e293b",
    paper_bgcolor="#1e293b",
    font=dict(family="Outfit, sans-serif", color="#cbd5e1"),
    xaxis=dict(gridcolor="#334155", zerolinecolor="#334155", tickfont=dict(color="#94a3b8")),
    yaxis=dict(gridcolor="#334155", zerolinecolor="#334155", tickfont=dict(color="#94a3b8")),
    margin=dict(l=10, r=10, t=30, b=10),
)

# ─── Data helpers ─────────────────────────────────────────────────────────────
def load_settings():
    default = {"monthly_budget": 10000.0}
    if not os.path.exists(SETTINGS_PATH):
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(default, f)
        return default
    try:
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    except Exception:
        return default

def save_settings(settings):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f)
    except Exception as e:
        st.error(f"Error saving settings: {e}")

def get_expenses_df():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame(columns=["transaction_date","source","amount","merchant",
                                     "account_ref","transaction_ref","vpa","category"])
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT transaction_date, source, amount, merchant, account_ref, "
        "transaction_ref, vpa, category FROM expenses ORDER BY transaction_date DESC",
        conn
    )
    conn.close()
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.date
    df['merchant'] = df['merchant'].fillna('').astype(str).str.strip().str.title()
    return df

def get_last_sync_time():
    """Returns the timestamp of the most recently logged transaction, or None."""
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM expenses")
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return datetime.datetime.strptime(row[0][:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None

def get_category_rules():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT pattern, category FROM category_rules ORDER BY pattern")
    rules = cursor.fetchall()
    conn.close()
    return rules

def run_db_backfill():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE expenses
        SET category = (
            SELECT category FROM category_rules
            WHERE instr(lower(expenses.merchant), lower(category_rules.pattern)) > 0
               OR instr(lower(expenses.vpa),      lower(category_rules.pattern)) > 0
            LIMIT 1
        )
    """)
    cursor.execute("UPDATE expenses SET category = 'Uncategorized' WHERE category IS NULL")
    conn.commit()
    conn.close()

# ─── KPI card renderer ────────────────────────────────────────────────────────
def render_kpi_card(title, value, sub=None, delta_str=None, is_delta_positive=True):
    sub_html   = f'<div class="metric-sub">{sub}</div>' if sub else ""
    delta_cls  = "delta-positive" if is_delta_positive else "delta-negative"
    delta_html = f'<div class="metric-delta {delta_cls}">{delta_str}</div>' if delta_str else ""
    return f"""
        <div class="metric-card-wrapper">
            <div class="metric-title">{title}</div>
            <div class="metric-value-text">{value}</div>
            {sub_html}
            {delta_html}
        </div>
    """

# ─── Budget progress bar (plain HTML — no markdown asterisks) ─────────────────
def render_budget_bar(value_pct, label_text, spent, budget, remaining=None):
    if value_pct > 1.0:
        bar_color = "#ef4444"
        status_color = "#f87171"
        status_bg = "rgba(239,68,68,0.08)"
        status_border = "#ef4444"
        status_icon = "⚠️"
        status_text = (f"Budget exceeded! Spent <strong>₹{spent:,.2f}</strong> — "
                       f"that's <strong>{value_pct*100:.1f}%</strong> of your "
                       f"₹{budget:,.2f} cap. Overspent by <strong>₹{spent-budget:,.2f}</strong>.")
    elif value_pct >= 0.8:
        bar_color = "#f59e0b"
        status_color = "#fbbf24"
        status_bg = "rgba(245,158,11,0.08)"
        status_border = "#f59e0b"
        status_icon = "⚠️"
        status_text = (f"High utilization. Spent <strong>₹{spent:,.2f}</strong> — "
                       f"<strong>{value_pct*100:.1f}%</strong> of your ₹{budget:,.2f} cap.")
    else:
        bar_color = "#FC8019"
        status_color = "#4ade80"
        status_bg = "rgba(74,222,128,0.08)"
        status_border = "#22c55e"
        status_icon = "✅"
        rem_str = f"<strong>₹{remaining:,.2f}</strong>" if remaining is not None else ""
        status_text = (f"Healthy budget. Spent <strong>₹{spent:,.2f}</strong> — "
                       f"<strong>{value_pct*100:.1f}%</strong> of your ₹{budget:,.2f} cap. "
                       f"{rem_str} remaining.")

    fill_pct = min(value_pct * 100, 100.0)
    st.html(f"""
        <div style="background:#1e293b;border:1px solid #334155;padding:22px 24px;
                    border-radius:16px;margin-bottom:24px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <span style="font-weight:600;color:#f1f5f9;font-size:15px;">{label_text}</span>
                <span style="font-weight:700;color:#FC8019;font-size:15px;">{value_pct*100:.1f}% Spent</span>
            </div>
            <div style="background:#334155;border-radius:10px;height:12px;width:100%;
                        overflow:hidden;margin-bottom:16px;">
                <div style="background:{bar_color};height:100%;width:{fill_pct}%;
                            border-radius:10px;transition:width 0.5s ease;"></div>
            </div>
            <div style="background:{status_bg};border-left:4px solid {status_border};
                        padding:12px 16px;border-radius:6px;color:{status_color};
                        font-size:14px;font-weight:500;line-height:1.6;">
                {status_icon} {status_text}
            </div>
        </div>
    """)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_dashboard, tab_rules = st.tabs(["📊 Expense Dashboard", "⚙️ Category Rules Manager"])

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.html("""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:28px;margin-top:10px;">
            <span style="font-size:34px;">💳</span>
            <div>
                <div style="font-size:21px;font-weight:700;color:#FC8019;line-height:1.1;">Orange Ledger</div>
                <div style="font-size:12px;color:#475569;">Gmail Sync Engine</div>
            </div>
        </div>
    """)

    # Last synced badge
    last_sync = get_last_sync_time()
    if last_sync:
        sync_label = last_sync.strftime("%-d %b %Y, %-I:%M %p")
        st.html(f"""
            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;
                        padding:8px 12px;margin-bottom:20px;display:flex;align-items:center;gap:8px;">
                <span style="font-size:11px;color:#4ade80;">●</span>
                <span style="font-size:12px;color:#94a3b8;">Last synced: <strong style="color:#cbd5e1;">{sync_label}</strong></span>
            </div>
        """)

    st.html('<div style="font-size:15px;font-weight:700;color:#f1f5f9;margin:4px 0 10px 0;letter-spacing:0.01em;">Settings</div>')
    settings = load_settings()
    current_budget = float(settings.get("monthly_budget", 10000.0))
    st.markdown("**Monthly Budget Cap (INR):**")
    new_budget = st.number_input(
        "Budget cap", min_value=500.0, max_value=1000000.0,
        value=current_budget, step=500.0, label_visibility="collapsed"
    )
    if new_budget != current_budget:
        settings["monthly_budget"] = new_budget
        save_settings(settings)
        st.success(f"Budget updated to ₹{new_budget:,.2f}!")

    st.markdown("---")
    st.html('<div style="font-size:15px;font-weight:700;color:#f1f5f9;margin:4px 0 8px 0;">Sync Controls</div>')
    st.write("Scan your Gmail inbox for new transaction alerts:")
    if st.button("🔄 Sync Gmail Transactions", use_container_width=True):
        with st.spinner("Connecting to Gmail and parsing new emails..."):
            try:
                result = subprocess.run(
                    ["python3", "local_expense_tracker.py"],
                    capture_output=True, text=True,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                run_db_backfill()
                # Detect if it fell back to offline/mock mode
                if "Falling back to OFFLINE DEMO MODE" in result.stdout:
                    st.warning("⚠️ Could not reach Gmail. No live data was synced — mock demo data was used instead. Check your credentials.")
                else:
                    st.success("Synchronization complete!")
                with st.expander("Sync Terminal Logs", expanded=False):
                    st.code(result.stdout or "No output.")
                    if result.stderr:
                        st.code("Errors/Warnings:\n" + result.stderr)
            except Exception as e:
                st.error(f"Failed to trigger sync: {e}")

    st.markdown("---")
    st.html('<div style="font-size:15px;font-weight:700;color:#f1f5f9;margin:4px 0 8px 0;">Engine Statistics</div>')
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM expenses")
        db_txns = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM category_rules")
        db_rules = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM expenses WHERE category = 'Uncategorized'")
        db_uncat = cursor.fetchone()[0]
        conn.close()
        st.html(f"""
            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;
                        padding:14px 16px;font-size:13px;line-height:2.0;">
                <div>📁 <span style="color:#94a3b8;">Transactions Logged:</span>
                     <strong style="color:#f1f5f9;"> {db_txns}</strong></div>
                <div>⚙️ <span style="color:#94a3b8;">Active Rules:</span>
                     <strong style="color:#f1f5f9;"> {db_rules}</strong></div>
                <div>🏷️ <span style="color:#94a3b8;">Uncategorized:</span>
                     <strong style="color:{'#f87171' if db_uncat > 0 else '#4ade80'};"> {db_uncat}</strong></div>
            </div>
        """)
    except Exception:
        st.info("Database not initialised yet.")

# ─── TAB 1: DASHBOARD ─────────────────────────────────────────────────────────
with tab_dashboard:
    df = get_expenses_df()

    if df.empty:
        st.warning("No transactions yet. Hit **Sync Gmail Transactions** in the sidebar.")
    else:
        # Timeline selector
        df['year_month'] = pd.to_datetime(df['transaction_date']).dt.strftime('%B %Y')
        months_list = sorted(df['year_month'].unique(),
                             key=lambda m: datetime.datetime.strptime(m, '%B %Y'),
                             reverse=True)
        timeline_options = ["All Time"] + list(months_list)

        st.html('<div class="timeline-selector-label">📅 Viewing Timeline</div>')
        sel_col, _ = st.columns([1, 2])
        with sel_col:
            selected_timeline = st.selectbox(
                "Timeline", timeline_options,
                index=1 if len(timeline_options) > 1 else 0,
                label_visibility="collapsed"
            )

        if selected_timeline == "All Time":
            timeline_df   = df.copy()
            timeline_label = "All-Time"
        else:
            timeline_df   = df[df['year_month'] == selected_timeline].copy()
            timeline_label = selected_timeline

        # ── KPI calculations ──────────────────────────────────────────────────
        this_spent   = timeline_df['amount'].sum()
        this_txns    = len(timeline_df)
        avg_ticket   = timeline_df['amount'].mean() if this_txns > 0 else 0
        top_series   = timeline_df.groupby('merchant')['amount'].sum().sort_values(ascending=False)
        top_merchant = top_series.index[0]   if not top_series.empty else "N/A"
        top_merch_v  = top_series.values[0]  if not top_series.empty else 0

        # MoM delta
        mom_str, is_pos = None, True
        if selected_timeline != "All Time":
            sel_dt = datetime.datetime.strptime(selected_timeline, '%B %Y')
            prev_month = (sel_dt.month - 2) % 12 + 1
            prev_year  = sel_dt.year - (1 if sel_dt.month == 1 else 0)
            df['_dt'] = pd.to_datetime(df['transaction_date'])
            prev_mask  = (df['_dt'].dt.year == prev_year) & (df['_dt'].dt.month == prev_month)
            prev_spent = df[prev_mask]['amount'].sum()
            delta      = this_spent - prev_spent
            mom_str    = f"₹{delta:+,.2f} vs prev month"
            is_pos     = delta >= 0

        all_time_spent = df['amount'].sum()

        # ── Four KPI cards (use st.html — avoids markdown tooltip corruption) ──
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.html(
                render_kpi_card(f"Spent — {timeline_label}", f"₹{this_spent:,.2f}",
                                delta_str=mom_str, is_delta_positive=is_pos))
        with c2:
            st.html(
                render_kpi_card("Total Spent", f"₹{all_time_spent:,.2f}",
                                sub=f"All-time · {len(df)} transactions"))
        with c3:
            st.html(
                render_kpi_card("Avg. Transaction",
                                f"₹{avg_ticket:,.2f}",
                                sub=f"{timeline_label} · {this_txns} txns"))
        with c4:
            st.html(
                render_kpi_card("Top Merchant",
                                top_merchant,
                                sub=f"₹{top_merch_v:,.2f} spent · {timeline_label}"))

        st.html('<hr class="section-divider">')

        # ── Budget bar ────────────────────────────────────────────────────────
        settings   = load_settings()
        budget_lim = float(settings.get("monthly_budget", 10000.0))
        pct_spent  = this_spent / budget_lim if budget_lim else 0
        remaining  = budget_lim - this_spent
        render_budget_bar(pct_spent, f"Budget Status — {timeline_label}",
                          this_spent, budget_lim, remaining if remaining > 0 else None)

        st.html('<hr class="section-divider">')

        # ── Charts ────────────────────────────────────────────────────────────
        chart_col1, chart_col2, chart_col3 = st.columns(3)

        # Chart 1: Area line — Spending Trend
        with chart_col1:
            st.html("<div style='font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:10px;'>📅 Spending Trend</div>")
            if selected_timeline == "All Time":
                trend_data = (
                    df.assign(_ym=pd.to_datetime(df['transaction_date']).dt.to_period('M').dt.to_timestamp())
                    .groupby('_ym')['amount'].sum().reset_index()
                )
                trend_data.columns = ['Date', 'Amount']
            else:
                trend_data = (
                    timeline_df.groupby('transaction_date')['amount'].sum()
                    .reset_index().rename(columns={'transaction_date': 'Date', 'amount': 'Amount'})
                )
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=trend_data['Date'], y=trend_data['Amount'],
                mode='lines+markers',
                fill='tozeroy',
                fillcolor='rgba(252,128,25,0.15)',
                line=dict(color='#FC8019', width=2.5),
                marker=dict(color='#FC8019', size=6, symbol='circle'),
                hovertemplate='<b>%{x}</b><br>₹%{y:,.2f}<extra></extra>',
            ))
            fig_trend.update_layout(**PLOTLY_DARK, height=280)
            st.plotly_chart(fig_trend, use_container_width=True)

        # Chart 2: Donut — Category Breakdown
        with chart_col2:
            st.html("<div style='font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:10px;'>🍩 Category Breakdown</div>")
            cat_data = (
                timeline_df.groupby('category')['amount'].sum()
                .reset_index().sort_values('amount', ascending=False)
            )
            DONUT_COLORS = [
                '#FC8019', '#10b981', '#fb7185', '#60a5fa',
                '#fbbf24', '#a78bfa', '#34d399', '#f472b6',
            ]
            fig_donut = go.Figure(go.Pie(
                labels=cat_data['category'],
                values=cat_data['amount'],
                hole=0.55,
                marker=dict(colors=DONUT_COLORS, line=dict(color='#0b0f19', width=2)),
                textinfo='percent',
                textfont=dict(size=12, color='#f1f5f9'),
                hovertemplate='<b>%{label}</b><br>₹%{value:,.2f}<br>%{percent}<extra></extra>',
            ))
            total_label = f'₹{cat_data["amount"].sum():,.0f}'
            fig_donut.update_layout(
                **PLOTLY_DARK,
                height=280,
                showlegend=True,
                legend=dict(
                    orientation='v', x=1.02, y=0.5,
                    font=dict(size=10, color='#94a3b8'),
                    bgcolor='rgba(0,0,0,0)',
                ),
                annotations=[dict(
                    text=f'<b>{total_label}</b>',
                    x=0.5, y=0.5, font=dict(size=13, color='#f1f5f9'),
                    showarrow=False,
                )],
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        # Chart 3: Horizontal bar with value labels — Top Merchants
        with chart_col3:
            st.html("<div style='font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:10px;'>🛍️ Top Merchants</div>")
            merch_data = (
                timeline_df.groupby('merchant')['amount'].sum()
                .reset_index().sort_values('amount', ascending=True).tail(8)
            )
            fig_merch = go.Figure(go.Bar(
                x=merch_data['amount'],
                y=merch_data['merchant'],
                orientation='h',
                marker=dict(
                    color=merch_data['amount'],
                    colorscale=[[0, '#fb7185'], [1, '#FC8019']],
                    showscale=False,
                    line=dict(width=0),
                ),
                text=[f'₹{v:,.0f}' for v in merch_data['amount']],
                textposition='outside',
                textfont=dict(color='#94a3b8', size=11),
                hovertemplate='<b>%{y}</b><br>₹%{x:,.2f}<extra></extra>',
            ))
            max_merch_val = merch_data['amount'].max() if not merch_data.empty else 100
            fig_merch.update_layout(**PLOTLY_DARK)
            fig_merch.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis=dict(
                    gridcolor='#334155', zerolinecolor='#334155',
                    tickfont=dict(color='#64748b', size=10),
                    showticklabels=False,
                    range=[0, max_merch_val * 1.2],
                ),
                yaxis=dict(
                    gridcolor='#334155', zerolinecolor='#334155',
                    tickfont=dict(color='#94a3b8', size=11),
                    automargin=True,
                ),
            )
            st.plotly_chart(fig_merch, use_container_width=True)

        st.html('<hr class="section-divider">')

        # ── Premium Transaction Feed ──────────────────────────────────────────
        # Category palette and emoji map
        CAT_STYLE = {
            'Food & Dining':          ('#FC8019', '#3d1f00', '🍔'),
            'Groceries':              ('#10b981', '#062318', '🛒'),
            'Entertainment & Subs':   ('#a78bfa', '#1e1040', '🎬'),
            'Travel':                 ('#60a5fa', '#0c1f40', '✈️'),
            'Shopping':               ('#f472b6', '#3d0a1f', '🛍️'),
            'Card Payment':           ('#fbbf24', '#3d2c00', '💳'),
            'BNPL / Finance':         ('#34d399', '#062318', '🏦'),
            'Utilities':              ('#94a3b8', '#1e293b', '⚡'),
            'Miscellaneous':          ('#64748b', '#0f172a', '📦'),
            'Uncategorized':          ('#475569', '#0f172a', '❓'),
        }
        SOURCE_COLORS = {
            'HDFC UPI':   ('#1d4ed8', '#1e3a8a'),
            'Amazon Pay': ('#FF9900', '#3d2200'),
        }

        def cat_badge(cat):
            fg, bg, icon = CAT_STYLE.get(cat, ('#64748b', '#1e293b', '•'))
            return (f'<span style="background:{bg};color:{fg};border:1px solid {fg}33;'
                    f'border-radius:20px;padding:2px 10px;font-size:11px;font-weight:600;'
                    f'white-space:nowrap;">{icon} {cat}</span>')

        def src_chip(src):
            fg, bg = SOURCE_COLORS.get(src, ('#94a3b8', '#1e293b'))
            return (f'<span style="background:{bg};color:{fg};border:1px solid {fg}44;'
                    f'border-radius:4px;padding:1px 7px;font-size:10px;font-weight:700;'
                    f'white-space:nowrap;letter-spacing:0.03em;">{src}</span>')

        st.html("<div style='font-size:20px;font-weight:700;color:#FC8019;margin-bottom:6px;'>🔎 Transactions</div>")

        # Filters row
        fcol1, fcol2, fcol3 = st.columns([3, 2, 2])
        with fcol1:
            search_q = st.text_input("🔍", placeholder="Search merchant, category…",
                                     label_visibility="collapsed")
        with fcol2:
            sources = ["All Sources"] + sorted(timeline_df['source'].unique().tolist())
            sel_src = st.selectbox("Source", sources, label_visibility="collapsed")
        with fcol3:
            cats_avail = ["All Categories"] + sorted(timeline_df['category'].dropna().unique().tolist())
            sel_cat = st.selectbox("Category", cats_avail, label_visibility="collapsed")

        # Apply filters
        filtered = timeline_df.copy()
        if search_q:
            filtered = filtered[
                filtered['merchant'].str.contains(search_q, case=False, na=False) |
                filtered['category'].str.contains(search_q, case=False, na=False) |
                filtered['transaction_ref'].str.contains(search_q, case=False, na=False)
            ]
        if sel_src != "All Sources":
            filtered = filtered[filtered['source'] == sel_src]
        if sel_cat != "All Categories":
            filtered = filtered[filtered['category'] == sel_cat]

        filtered = filtered.sort_values('transaction_date', ascending=False)
        total_filtered = filtered['amount'].sum()
        count_filtered = len(filtered)

        # Summary strip
        st.html(f"""
            <div style="display:flex;gap:24px;margin:8px 0 16px 0;">
                <span style="font-size:13px;color:#64748b;">
                    <strong style="color:#f1f5f9;">{count_filtered}</strong> transactions
                </span>
                <span style="font-size:13px;color:#64748b;">
                    Total: <strong style="color:#FC8019;">₹{total_filtered:,.2f}</strong>
                </span>
            </div>
        """)

        if filtered.empty:
            st.html("<div style='text-align:center;padding:40px;color:#475569;font-size:14px;'>No transactions match your filters.</div>")
        else:
            # Group by date
            filtered['_date'] = pd.to_datetime(filtered['transaction_date'])
            grouped = filtered.groupby('_date', sort=False)
            date_keys = sorted(filtered['_date'].unique(), reverse=True)

            rows_html = ""
            for date_val in date_keys:
                day_df = filtered[filtered['_date'] == date_val]
                day_total = day_df['amount'].sum()
                day_label = pd.Timestamp(date_val).strftime('%-d %B %Y')
                day_weekday = pd.Timestamp(date_val).strftime('%A')

                rows_html += f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:10px 16px 6px 16px;margin-top:8px;">
                    <span style="font-size:12px;font-weight:700;color:#64748b;
                                 text-transform:uppercase;letter-spacing:0.08em;">
                        {day_weekday}, {day_label}
                    </span>
                    <span style="font-size:12px;color:#475569;">₹{day_total:,.2f}</span>
                </div>
                """

                for _, row in day_df.iterrows():
                    _, _, icon = CAT_STYLE.get(row['category'], ('#64748b', '#1e293b', '•'))
                    badge_html  = cat_badge(row.get('category', 'Uncategorized'))
                    chip_html   = src_chip(row.get('source', ''))
                    merch_name  = str(row['merchant']).title()
                    amt         = row['amount']

                    rows_html += f"""
                    <div style="display:flex;align-items:center;gap:14px;
                                padding:12px 16px;border-bottom:1px solid #1e293b;
                                transition:background 0.15s;"
                         onmouseover="this.style.background='rgba(252,128,25,0.04)'"
                         onmouseout="this.style.background='transparent'">

                        <!-- Icon circle -->
                        <div style="width:40px;height:40px;border-radius:12px;
                                    background:#1e293b;display:flex;align-items:center;
                                    justify-content:center;font-size:18px;flex-shrink:0;">
                            {icon}
                        </div>

                        <!-- Merchant + meta -->
                        <div style="flex:1;min-width:0;">
                            <div style="font-size:14px;font-weight:600;color:#f1f5f9;
                                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                                {merch_name}
                            </div>
                            <div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap;
                                        align-items:center;">
                                {badge_html}
                                {chip_html}
                            </div>
                        </div>

                        <!-- Amount -->
                        <div style="font-size:16px;font-weight:700;color:#FC8019;
                                    white-space:nowrap;flex-shrink:0;">
                            ₹{amt:,.2f}
                        </div>
                    </div>
                    """

            st.html(f"""
                <div style="background:#111827;border:1px solid #1e293b;border-radius:16px;
                            overflow:hidden;margin-bottom:20px;">
                    {rows_html}
                </div>
            """)

        # CSV export
        export_df = filtered[["transaction_date","source","amount","merchant",
                               "category","account_ref","transaction_ref","vpa"]]
        csv = export_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export to CSV",
            data=csv,
            file_name=f"ledger_{selected_timeline.replace(' ','_')}_{datetime.date.today()}.csv",
            mime="text/csv",
        )

# ─── TAB 2: RULES MANAGER ─────────────────────────────────────────────────────
with tab_rules:
    st.header("⚙️ Category Rules Manager")
    st.write("Create, modify, and delete keyword rules that auto-categorize transactions.")

    col_list, col_form = st.columns([2, 1])

    with col_list:
        st.subheader("Active Rules")
        rules = get_category_rules()
        if not rules:
            st.info("No rules found. Add one on the right.")
        else:
            st.dataframe(pd.DataFrame(rules, columns=["Pattern Keyword", "Assigned Category"]),
                         use_container_width=True, hide_index=True)

    with col_form:
        st.subheader("Add Rule")
        with st.form("add_rule_form", clear_on_submit=True):
            pattern = st.text_input("Keyword (e.g. 'uber', 'blinkit'):").strip()
            categories_list = [
                "Food & Dining", "Groceries", "Entertainment & Subs",
                "Card Payment", "Shopping", "Travel", "Utilities",
                "BNPL / Finance", "Miscellaneous"
            ]
            category = st.selectbox("Category:", categories_list)
            if st.form_submit_button("Save Rule & Sync"):
                if not pattern:
                    st.error("Pattern cannot be blank.")
                else:
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        conn.cursor().execute(
                            "INSERT OR REPLACE INTO category_rules (pattern, category) VALUES (?, ?)",
                            (pattern.lower(), category)
                        )
                        conn.commit(); conn.close()
                        run_db_backfill()
                        st.success(f"Rule saved: '{pattern}' → '{category}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

        st.subheader("Delete Rule")
        rules = get_category_rules()
        if rules:
            with st.form("delete_rule_form"):
                sel_pat = st.selectbox("Pattern to delete:", [r[0] for r in rules])
                if st.form_submit_button("Delete & Re-sync"):
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        conn.cursor().execute("DELETE FROM category_rules WHERE pattern = ?", (sel_pat,))
                        conn.commit(); conn.close()
                        run_db_backfill()
                        st.success(f"Deleted rule for '{sel_pat}'.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")
