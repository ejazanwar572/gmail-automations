import datetime
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Setup paths
CARD_DIR = Path(__file__).resolve().parent
ROOT_DIR = CARD_DIR.parent
sys.path.insert(0, str(CARD_DIR))
sys.path.insert(0, str(ROOT_DIR))

import dcbm_engine

# ─── Page Configuration ────────────────────────────────────────────────────────
try:
    st.set_page_config(
        page_title="HDFC Diners Black Metal · Control Center",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
except Exception:
    pass

# ─── Multi-Card Router Gate ───────────────────────────────────────────────────
if "selected_card" in st.session_state and "HSBC" in str(st.session_state["selected_card"]):
    hsbc_app_path = ROOT_DIR / "HSBC Live Plus Statements" / "hsbc_live_plus_app.py"
    if hsbc_app_path.exists():
        import runpy
        runpy.run_path(str(hsbc_app_path), run_name="__main__")
        st.stop()

# Theme Palette: Modern Executive Slate & Brushed Champagne
T = {
    "app_bg": "#f8fafc",
    "text_main": "#0f172a",
    "text_muted": "#475569",
    "text_sub": "#64748b",
    "border": "#e2e8f0",
    "border_sub": "#f1f5f9",
    "card_bg": "#ffffff",
    "card_border": "#e2e8f0",
    "card_shadow": "0 1px 3px rgba(15, 23, 42, 0.04), 0 8px 24px -4px rgba(15, 23, 42, 0.06)",
    "hero_bg": "#ffffff",
    "hero_border": "#e2e8f0",
    "hero_shadow": "0 1px 3px rgba(180, 120, 32, 0.06), 0 12px 32px -4px rgba(15, 23, 42, 0.08)",
    "subcard_bg": "#f8fafc",
    "subcard_border": "#e2e8f0",
    "input_bg": "#ffffff",
    "input_border": "#cbd5e1",
    "input_text": "#0f172a",
    "input_focus_border": "#b47820",
    "input_focus_shadow": "rgba(180, 120, 32, 0.2)",
    "btn_bg": "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
    "btn_hover": "linear-gradient(135deg, #334155 0%, #1e293b 100%)",
    "btn_border": "#334155",
    "btn_shadow": "0 2px 8px rgba(15, 23, 42, 0.15)",
    "progress_bg": "#e2e8f0",
    "progress_fill": "linear-gradient(90deg, #b47820 0%, #d4a359 100%)",
    "chip_bg": "#ffffff",
    "chip_border": "#e2e8f0",
    "card_number_badge_bg": "#f1f5f9",
    "card_number_badge_border": "#cbd5e1",
    "card_number_badge_color": "#0f172a",
    "footer_border": "#e2e8f0",
    "footer_text": "#64748b",
    "val_hl_bg": "#f8fafc",
    "val_hl_border": "#e2e8f0",
    "accent_gold": "#b47820",
    "accent_green": "#16a34a",
    "accent_amber": "#d97706",
}

st.html(
    f"""
    <style>
    /* Hallmark · app: hdfc-dcbm · scope: app · theme: Haute Metal · v2.0.0 */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    :root {{
        --bg-canvas: #f8fafc;
        --bg-card: #ffffff;
        --bg-subcard: #f8fafc;
        --text-main: #0f172a;
        --text-muted: #475569;
        --text-sub: #64748b;
        --border-sub: #f1f5f9;
        --border-default: #e2e8f0;
        --border-strong: #cbd5e1;
        --accent-gold: #b47820;
        --accent-gold-dark: #8c5310;
        --accent-gold-light: #d4a359;
        --accent-green: #16a34a;
        --accent-amber: #d97706;
        --accent-red: #ef4444;
        --progress-bg: #e2e8f0;
        --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.04);
        --shadow-card: 0 1px 3px rgba(15, 23, 42, 0.04), 0 8px 24px -4px rgba(15, 23, 42, 0.06);
        --shadow-hero: 0 1px 3px rgba(180, 120, 32, 0.06), 0 12px 32px -4px rgba(15, 23, 42, 0.08);
    }}

    html, body, [class*="css"], .stMarkdown, p, div, label, span, h1, h2, h3, h4, h5, h6 {{
        font-family: 'Outfit', sans-serif !important;
    }}

    /* Tabular numbers for financial and metric clarity */
    .hero-number, .tabular-num, [data-testid="stDataFrame"], table, .pill {{
        font-variant-numeric: tabular-nums lining-nums;
    }}

    /* Focus-visible rings for high keyboard accessibility */
    *:focus-visible {{
        outline: 2px solid var(--accent-gold) !important;
        outline-offset: 2px !important;
    }}

    /* Preserve Material ligature icons */
    [data-testid="stIconMaterial"], .material-symbols-rounded, span[data-testid="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded' !important;
        font-weight: normal !important;
        font-style: normal !important;
        font-size: 20px !important;
        line-height: 1 !important;
        display: inline-block !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        -webkit-font-feature-settings: 'liga' !important;
        -webkit-font-smoothing: antialiased !important;
    }}

    .stApp {{
        background-color: var(--bg-canvas) !important;
        color: var(--text-main) !important;
    }}

    /* Top header space removal */
    [data-testid="stToolbar"], #stDecoration {{ display: none !important; }}
    header[data-testid="stHeader"] {{
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        background-color: var(--bg-canvas) !important;
    }}
    [data-testid="stAppViewBlockContainer"] {{
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }}

    /* Card container */
    .metal-card {{
        background: var(--bg-card);
        border: 1px solid var(--border-default);
        border-radius: 16px;
        padding: 24px;
        box-shadow: var(--shadow-card);
        margin-bottom: 20px;
        transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
    }}
    .metal-card:hover {{
        border-color: var(--border-strong);
    }}

    /* Hero Card */
    .hero-card {{
        background: var(--bg-card);
        border: 1px solid var(--border-default);
        border-radius: 18px;
        padding: 26px;
        box-shadow: var(--shadow-hero);
        margin-bottom: 24px;
    }}

    /* Badge Pills - Untracked, calm typography */
    .pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 11px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        text-transform: none;
        letter-spacing: normal;
        line-height: 1.4;
    }}
    .pill-green {{
        background: #ecfdf5;
        color: #059669;
        border: 1px solid #a7f3d0;
    }}
    .pill-orange {{
        background: #fffbeb;
        color: #d97706;
        border: 1px solid #fde68a;
    }}
    .pill-red {{
        background: #fef2f2;
        color: #dc2626;
        border: 1px solid #fecaca;
    }}
    .pill-blue {{
        background: #f1f5f9;
        color: #0f172a;
        border: 1px solid #cbd5e1;
    }}
    .pill-gold {{
        background: #fffbeb;
        color: #b47820;
        border: 1px solid #fde68a;
    }}

    /* Status dot indicator */
    .status-dot {{
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: var(--accent-gold);
        display: inline-block;
    }}
    .status-dot-green {{
        background-color: var(--accent-green);
    }}

    /* Big metric numbers */
    .hero-number {{
        font-size: 42px;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.05;
        color: var(--text-main);
        font-variant-numeric: tabular-nums lining-nums;
    }}
    .hero-sub {{
        font-size: 13.5px;
        color: var(--text-muted);
        font-weight: 500;
        margin-top: 4px;
    }}

    /* Buttons & Download Buttons - Targeted transitions */
    div.stButton > button, div[data-testid="stDownloadButton"] > button {{
        background: {T["btn_bg"]} !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        border: 1px solid {T["btn_border"]} !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 8px 18px !important;
        box-shadow: {T["btn_shadow"]} !important;
        transition: background-color 150ms ease, border-color 150ms ease, transform 150ms ease, box-shadow 150ms ease !important;
    }}
    div.stButton > button:hover, div[data-testid="stDownloadButton"] > button:hover {{
        background: {T["btn_hover"]} !important;
        border-color: #d97706 !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
    }}

    /* Input controls: Selectboxes, Text Inputs, Multiselects */
    .stTextInput input, .stNumberInput input {{
        background-color: var(--bg-subcard) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 10px !important;
        font-size: 14px !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus {{
        border-color: var(--accent-gold) !important;
        box-shadow: 0 0 0 2px rgba(154, 96, 20, 0.2) !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: var(--bg-subcard) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 10px !important;
        font-size: 14px !important;
    }}
    div[data-baseweb="select"] span {{
        color: var(--text-main) !important;
    }}
    span[data-baseweb="tag"] {{
        background-color: var(--accent-gold) !important;
        border: 1px solid var(--accent-gold-light) !important;
        border-radius: 6px !important;
        color: #ffffff !important;
    }}

    /* Expanders */
    [data-testid="stExpander"] details summary svg {{
        min-width: 1rem;
        min-height: 1rem;
    }}
    [data-testid="stExpander"] details summary p {{
        font-weight: 600 !important;
        font-size: 14.5px !important;
        color: var(--text-main) !important;
    }}
    [data-testid="stExpander"] {{
        border: 1px solid var(--border-default) !important;
        border-radius: 12px !important;
        background: var(--bg-card) !important;
    }}

    /* Streamlit Segmented Control (Theme Toggle) & Header Buttons */
    div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) {{
        align-items: center !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) div[data-testid="stVerticalBlock"] {{
        gap: 0 !important;
        justify-content: center !important;
        align-items: center !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) div[data-testid="stButtonGroup"] button {{
        height: 36px !important;
        min-height: 36px !important;
        max-height: 36px !important;
        padding: 0 10px !important;
        font-size: 12.5px !important;
        line-height: 36px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) div.stButton > button {{
        height: 36px !important;
        min-height: 36px !important;
        max-height: 36px !important;
        padding: 0 14px !important;
        font-size: 13px !important;
        line-height: 36px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) .pill {{
        height: 36px !important;
        min-height: 36px !important;
        line-height: 36px !important;
        padding: 0 10px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 8px !important;
        box-sizing: border-box !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) .stMarkdown {{
        margin: 0 !important;
        padding: 0 !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) div[data-testid="stMarkdownContainer"] {{
        margin: 0 !important;
        padding: 0 !important;
    }}

    /* Tabs Styling */
    button[data-baseweb="tab"] {{
        font-weight: 600 !important;
        font-size: 14px !important;
        color: var(--text-muted) !important;
        letter-spacing: normal !important;
        text-transform: none !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: var(--accent-gold) !important;
        border-bottom-color: var(--accent-gold) !important;
        font-weight: 700 !important;
    }}

    /* Streamlit Dataframe */
    div[data-testid="stDataFrame"] {{
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid var(--border-default) !important;
    }}

    /* Selectbox for Card Switcher */
    div[data-testid="stSelectbox"] {{
        margin-bottom: 0px !important;
    }}
    div[data-testid="stSelectbox"] .react-aria-ComboBox,
    div[data-testid="stSelectbox"] div[data-rac=""][role="group"],
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {{
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: 1px solid var(--border-default) !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 14.5px !important;
        color: var(--text-main) !important;
        box-shadow: var(--shadow-sm) !important;
        height: 38px !important;
        min-height: 38px !important;
        transition: border-color 150ms ease, box-shadow 150ms ease !important;
    }}
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        height: 36px !important;
        min-height: 36px !important;
    }}
    div[data-testid="stSelectbox"] div[data-rac=""][role="group"]:hover,
    div[data-testid="stSelectbox"] div[data-rac=""][role="group"]:focus-within,
    div[data-testid="stSelectbox"] div[data-baseweb="select"]:hover,
    div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {{
        border-color: var(--accent-gold) !important;
        box-shadow: 0 2px 8px rgba(154, 96, 20, 0.15) !important;
    }}
    div[data-testid="stSelectbox"] input {{
        color: var(--text-main) !important;
        font-weight: 700 !important;
        font-size: 14.5px !important;
        font-family: 'Outfit', sans-serif !important;
        background: transparent !important;
    }}
    div[data-testid="stSelectbox"] * {{
        color: var(--text-main) !important;
        font-family: 'Outfit', sans-serif !important;
    }}
    div[data-baseweb="popover"] {{
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18) !important;
    }}
    div[data-baseweb="menu"] {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: 12px !important;
        padding: 6px !important;
    }}
    li[data-baseweb="menu-item"] {{
        border-radius: 8px !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
        color: var(--text-main) !important;
        padding: 8px 12px !important;
        margin-bottom: 2px !important;
    }}
    li[data-baseweb="menu-item"]:hover {{
        background-color: var(--bg-subcard) !important;
        color: var(--accent-gold) !important;
    }}
    li[data-baseweb="menu-item"][aria-selected="true"] {{
        background-color: rgba(154, 96, 20, 0.1) !important;
        color: var(--accent-gold) !important;
        font-weight: 700 !important;
    }}

    /* Mobile Responsive */
    @media (max-width: 768px) {{
        [data-testid="stAppViewBlockContainer"] {{
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            padding-top: 0.6rem !important;
        }}

        .hero-card, .metal-card {{
            height: auto !important;
            min-height: 0 !important;
            padding: 16px !important;
            margin-bottom: 14px !important;
            border-radius: 14px !important;
        }}

        .hero-number {{
            font-size: 32px !important;
        }}

        .mobile-header-title {{
            font-size: 18px !important;
            line-height: 1.3 !important;
            display: flex !important;
            flex-wrap: wrap !important;
            align-items: center !important;
            gap: 6px !important;
        }}

        .mobile-card-badge {{
            font-size: 12px !important;
            margin-left: 0 !important;
            padding: 2px 7px !important;
            display: inline-block !important;
        }}

        .mobile-header-sub {{
            font-size: 11.5px !important;
            margin-top: 3px !important;
            line-height: 1.3 !important;
        }}

        div[data-baseweb="tab-list"] {{
            overflow-x: auto !important;
            white-space: nowrap !important;
            scrollbar-width: none !important;
            -webkit-overflow-scrolling: touch !important;
            display: flex !important;
            flex-wrap: nowrap !important;
            gap: 4px !important;
            padding-bottom: 4px !important;
        }}
        div[data-baseweb="tab-list"]::-webkit-scrollbar {{
            display: none !important;
        }}
        button[data-baseweb="tab"] {{
            flex-shrink: 0 !important;
            font-size: 13px !important;
            padding: 8px 12px !important;
        }}

        div.stButton > button, div[data-testid="stDownloadButton"] > button {{
            padding: 7px 14px !important;
            font-size: 13px !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.mobile-card-badge) {{
            display: flex !important;
            flex-direction: column !important;
            flex-wrap: wrap !important;
            gap: 12px !important;
            width: 100% !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.mobile-card-badge) > div[data-testid="stColumn"] {{
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            flex: 1 1 100% !important;
            margin: 0 !important;
            left: 0 !important;
            right: 0 !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn):not(:has(.mobile-card-badge)) {{
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: flex-end !important;
            gap: 8px !important;
            width: 100% !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn):not(:has(.mobile-card-badge)) > div[data-testid="stColumn"] {{
            min-width: 0 !important;
            max-width: none !important;
            width: auto !important;
            flex: 1 1 auto !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn):not(:has(.mobile-card-badge)) > div[data-testid="stColumn"]:first-child {{
            flex: 1 1 auto !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn):not(:has(.mobile-card-badge)) > div[data-testid="stColumn"]:last-child {{
            flex: 0 0 auto !important;
        }}
    }}
    </style>
    """
)

# ─── Load Data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data():
    alerts_file = CARD_DIR / "gmail_alerts.json"
    if not alerts_file.exists():
        try:
            dcbm_engine.trigger_live_sync(CARD_DIR)
        except Exception:
            pass
    return dcbm_engine.compute_all_dashboard_data(CARD_DIR)

data = load_data()

# ─── Top Header Bar ───────────────────────────────────────────────────────────
col_head_left, col_head_right = st.columns([2.8, 1.2], vertical_alignment="center")

with col_head_left:
    sub_c1, sub_c2 = st.columns([0.08, 0.92], vertical_alignment="center")
    with sub_c1:
        st.html(
            f"""
            <div style="width: 38px; height: 38px; background: #faf8f4; color: {T['accent_gold']}; border-radius: 8px; display: flex; align-items: center; justify-content: center; border: 1px solid {T['border']};">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{T['accent_gold']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="2" y="5" width="20" height="14" rx="2"/>
                    <line x1="2" y1="10" x2="22" y2="10"/>
                </svg>
            </div>
            """
        )
    with sub_c2:
        card_col, badge_col = st.columns([1.5, 1.2], vertical_alignment="center")
        with card_col:
            st.html(
                f"""
                <div style="font-size: 11px; font-weight: 600; color: #b47820; margin-bottom: 3px;">
                    Selected card account
                </div>
                """
            )
            card_options = ["HDFC Diners Club Black Metal", "HSBC Live+ Credit Card"]
            current_card = st.session_state.get("selected_card", "HDFC Diners Club Black Metal")
            if current_card not in card_options:
                current_card = "HDFC Diners Club Black Metal"

            def on_hdfc_card_change():
                st.session_state["selected_card"] = st.session_state["active_card_switcher"]

            st.selectbox(
                "Credit Card",
                options=card_options,
                index=card_options.index(current_card),
                key="active_card_switcher",
                on_change=on_hdfc_card_change,
                label_visibility="collapsed",
            )
        with badge_col:
            st.html(
                f"""
                <div style="margin-top: 15px; display: flex; align-items: center; gap: 8px;">
                    <span class="mobile-card-badge" style="font-size: 13px; font-weight: 700; color: {T['card_number_badge_color']}; background: {T['card_number_badge_bg']}; padding: 3px 10px; border-radius: 8px; border: 1px solid {T['card_number_badge_border']};">
                        •••• 2360
                    </span>
                    <span class="pill pill-blue" style="font-size: 11px;">
                        Diners Club Metal
                    </span>
                </div>
                """
            )
        st.html(
            f"""
            <div class="mobile-header-sub" style="font-size: 13px; color: {T['text_sub']}; font-weight: 500; margin-top: 2px;">
                Automated Real-Time Rewards & Spend Tracker from Gmail InstaAlerts
            </div>
            """
        )

with col_head_right:
    btn_sync, btn_time = st.columns([1.1, 1.0], vertical_alignment="center")
    with btn_sync:
        st.html("<div class='mobile-sync-btn' style='display:none;'></div>")
        if st.button("Sync alerts", use_container_width=True):
            with st.spinner("Fetching latest alerts from Gmail..."):
                try:
                    sync_res = dcbm_engine.trigger_live_sync(CARD_DIR)
                    st.cache_data.clear()
                    st.toast(f"Synced {sync_res.get('alert_count', 0)} alerts")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Sync error: {exc}")
    with btn_time:
        sync_time_str = data["sync_metadata"]["last_synced"]
        try:
            dt = datetime.datetime.fromisoformat(sync_time_str)
            friendly_time = dt.strftime("%d %b %H:%M")
        except Exception:
            friendly_time = "Live"
        st.html(
            f"""
            <div style="text-align: right;">
                <span class="pill pill-blue" style="font-size: 11px; white-space: nowrap; padding: 4px 10px; gap: 6px;">
                    <span class="status-dot"></span> {friendly_time}
                </span>
            </div>
            """
        )

# ─── SECTION 1: HERO CAP MONITOR ──────────────────────────────────────────────
st.html("<div style='height: 10px;'></div>")

# HDFC Bank enforces the 10,000 accelerated cap strictly by Calendar Month (1st to last day of month).
active_cap = data["caps"]["calendar_month"]
cycle_title = f"{datetime.date.today().strftime('%B %Y')} Limit"
cycle_subtitle = f"Resets on {active_cap['reset_date']} • {active_cap['days_remaining']} days remaining"
policy_note = "Official HDFC Rule: SmartBuy accelerated cap resets on the 1st of every calendar month."

# Reward Points Metrics for Portfolio Tile
pts_summary = data["points_summary"]
lifetime_earned = pts_summary.get("total_estimated", 0)
current_available = pts_summary.get("net_available", 0)
total_spend_all = sum(t["amount"] for t in data["transactions"])
lifetime_reward_rate = (lifetime_earned / total_spend_all * 100) if total_spend_all > 0 else 0.0

# Render Hero Cards (Bento Grid)
hero_col_left, hero_col_right = st.columns([1.7, 1.3])

with hero_col_left:
    today_earned = active_cap.get("today_earned", 0)
    today_daily_cap = active_cap.get("daily_cap", 2500)
    today_percent = min(100.0, round((today_earned / today_daily_cap) * 100, 1)) if today_daily_cap > 0 else 0.0

    st.html(
        f"""
        <div class="hero-card" style="padding: 24px; display: flex; flex-direction: column; justify-content: space-between; min-height: 270px;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                    <div>
                        <div style="font-size: 11.5px; font-weight: 600; color: #b47820;">
                            SmartBuy accelerated points limit
                        </div>
                        <div style="font-size: 20px; font-weight: 700; color: var(--text-main); margin-top: 1px;">
                            {cycle_title}
                        </div>
                    </div>
                    <span class="pill pill-gold" style="font-size: 11.5px; padding: 4px 10px; white-space: nowrap;">
                        {'Resets today' if active_cap['days_remaining'] == 0 else ('Resets tomorrow' if active_cap['days_remaining'] == 1 else f"Resets in {active_cap['days_remaining']}d")} · {active_cap['reset_date']}
                    </span>
                </div>
                <div style="display: flex; align-items: baseline; gap: 8px;">
                    <span class="hero-number tabular-num">{active_cap["remaining"]:,}</span>
                    <span style="font-size: 16px; font-weight: 600; color: var(--text-muted);">/ {active_cap["monthly_cap"]:,} RP remaining</span>
                </div>
                <div class="hero-sub">{active_cap["percent_remaining"]}% monthly headroom still available to earn</div>
            </div>
            <div style="margin-top: 14px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); margin-bottom: 5px;">
                    <span>Monthly progress: <b class="tabular-num">{active_cap["earned"]:,} / {active_cap["monthly_cap"]:,} RP ({active_cap['percent_used']}%)</b></span>
                    <span>Today: <b class="tabular-num">{today_earned:,} / {today_daily_cap:,} RP</b></span>
                </div>
                <div style="background: var(--progress-bg); border-radius: 999px; height: 9px; overflow: hidden; margin-bottom: 12px;">
                    <div style="background: {T['progress_fill']}; width: {min(100.0, active_cap['percent_used'])}%; height: 100%;"></div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div style="background: var(--bg-subcard); padding: 10px 14px; border-radius: 10px; border: 1px solid var(--border-default); display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 11.5px; color: var(--text-muted); font-weight: 600;">Flights · SmartBuy 5x</div>
                            <div style="font-size: 18px; font-weight: 800; color: #b47820;" class="tabular-num">₹{active_cap["flight_spend_capacity"]:,}</div>
                        </div>
                        <span style="font-size: 11px; color: var(--text-sub); text-align: right;">4x bonus<br>(20 RP / ₹150)</span>
                    </div>
                    <div style="background: var(--bg-subcard); padding: 10px 14px; border-radius: 10px; border: 1px solid var(--border-default); display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 11.5px; color: var(--text-muted); font-weight: 600;">Hotels · SmartBuy 10x</div>
                            <div style="font-size: 18px; font-weight: 800; color: #0f172a;" class="tabular-num">₹{active_cap["hotel_spend_capacity"]:,}</div>
                        </div>
                        <span style="font-size: 11px; color: var(--text-sub); text-align: right;">9x bonus<br>(45 RP / ₹150)</span>
                    </div>
                </div>
            </div>
        </div>
        """
    )

with hero_col_right:
    st.html(
        f"""
        <div class="metal-card" style="padding: 24px; display: flex; flex-direction: column; justify-content: space-between; min-height: 270px; box-sizing: border-box;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 11.5px; font-weight: 600; color: var(--text-muted);">
                        Reward points portfolio
                    </div>
                    <span class="pill pill-green" style="font-size: 11px; padding: 3px 8px;">
                        1 RP = ₹1.00 SmartBuy
                    </span>
                </div>
                <div style="font-size: 12px; color: var(--text-sub);">
                    Available SmartBuy travel booking value
                </div>
                <div style="margin-top: 4px;">
                    <span class="hero-number tabular-num" style="color: #059669;">₹{current_available:,}</span>
                </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px;">
                <div style="background: var(--bg-subcard); padding: 8px 12px; border-radius: 10px; border: 1px solid var(--border-default); display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 11.5px; color: var(--text-muted); font-weight: 600;">Lifetime reward points</div>
                        <div style="font-size: 10.5px; color: var(--text-sub);">Total points earned to date</div>
                    </div>
                    <div style="text-align: right;" class="tabular-num">
                        <span style="font-size: 16px; font-weight: 700; color: #b47820;">{lifetime_earned:,}</span>
                        <span style="font-size: 11px; font-weight: 600; color: var(--text-muted);"> RP</span>
                    </div>
                </div>
                <div style="background: var(--bg-subcard); padding: 8px 12px; border-radius: 10px; border: 1px solid var(--border-default); display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 11.5px; color: var(--text-muted); font-weight: 600;">Current spendable balance</div>
                        <div style="font-size: 10.5px; color: var(--text-sub);">Net liquid reward points</div>
                    </div>
                    <div style="text-align: right;" class="tabular-num">
                        <span style="font-size: 16px; font-weight: 700; color: #0f172a;">{current_available:,}</span>
                        <span style="font-size: 11px; font-weight: 600; color: var(--text-muted);"> RP</span>
                    </div>
                </div>
                <div style="background: var(--bg-subcard); padding: 8px 12px; border-radius: 10px; border: 1px solid var(--border-default); display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 11.5px; color: var(--text-muted); font-weight: 600;">Net reward rate</div>
                        <div style="font-size: 10.5px; color: var(--text-sub);">{lifetime_earned:,} RP / ₹{total_spend_all:,.0f} spend</div>
                    </div>
                    <div style="text-align: right;" class="tabular-num">
                        <span style="font-size: 16px; font-weight: 700; color: #059669;">{lifetime_reward_rate:.2f}%</span>
                    </div>
                </div>
            </div>
        </div>
        """
    )

# ─── SECTION 2: MILESTONES ROW ────────────────────────────────────────────────
st.html(f"<div style='font-size: 18px; font-weight: 700; margin: 10px 0 14px 0; color: var(--text-main);'>Spend milestones & fee waiver</div>")

m_col1, m_col2, m_col3 = st.columns(3)

# 1. Welcome Milestone
welcome = data["milestones"]["welcome"]
with m_col1:
    status_tag = "Unlocked" if welcome["met"] else f"{welcome['days_left']}d remaining"
    tag_class = "pill-green" if welcome["met"] else "pill-blue"
    st.html(
        f"""
        <div class="metal-card" style="min-height: 236px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <div style="font-size: 12px; font-weight: 600; color: var(--text-muted);">Welcome milestone</div>
                        <div style="font-size: 16px; font-weight: 700; color: var(--text-main);">₹1.5 Lakhs in 90 Days</div>
                    </div>
                    <span class="pill {tag_class}">{status_tag}</span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: #15803d; margin: 6px 0;" class="tabular-num">
                    ₹{welcome["spend"]:,.0f} <span style="font-size: 14px; font-weight: 500; color: var(--text-sub);">/ ₹{welcome["target"]:,.0f}</span>
                    <span style="font-size: 13px; font-weight: 700; color: #15803d; margin-left: 6px;">({welcome['progress']}%)</span>
                </div>
                <div style="background: var(--progress-bg); border-radius: 999px; height: 8px; margin: 8px 0; overflow: hidden;">
                    <div style="background: #15803d; width: {welcome['progress']}%; height: 100%;"></div>
                </div>
            </div>
            <div style="background: var(--bg-subcard); border: 1px solid var(--border-default); border-radius: 10px; padding: 9px 12px; display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                <div>
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-sub);">Perks status</div>
                    <div style="font-size: 13px; font-weight: 800; color: #15803d;">Unlocked & claimed</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-sub);">Memberships</div>
                    <div style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Club Marriott · Prime · Swiggy</div>
                </div>
            </div>
        </div>
        """
    )

# 2. Quarterly Milestone
q_bonus = data["milestones"]["quarterly"]
with m_col2:
    q_tag = "Unlocked" if q_bonus["met"] else f"{q_bonus['days_left']}d remaining"
    q_class = "pill-green" if q_bonus["met"] else "pill-orange"
    st.html(
        f"""
        <div class="metal-card" style="min-height: 236px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <div style="font-size: 12px; font-weight: 600; color: var(--text-muted);">Quarterly bonus ({q_bonus['label']})</div>
                        <div style="font-size: 16px; font-weight: 700; color: var(--text-main);">10,000 Bonus RP</div>
                    </div>
                    <span class="pill {q_class}">{q_tag}</span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: #b45309; margin: 6px 0;" class="tabular-num">
                    ₹{q_bonus["spend"]:,.0f} <span style="font-size: 14px; font-weight: 500; color: var(--text-sub);">/ ₹{q_bonus["target"]:,.0f}</span>
                    <span style="font-size: 13px; font-weight: 700; color: #b45309; margin-left: 6px;">({q_bonus['progress']}%)</span>
                </div>
                <div style="background: var(--progress-bg); border-radius: 999px; height: 8px; margin: 8px 0; overflow: hidden;">
                    <div style="background: #b45309; width: {q_bonus['progress']}%; height: 100%;"></div>
                </div>
            </div>
            <div style="background: var(--bg-subcard); border: 1px solid var(--border-default); border-radius: 10px; padding: 9px 12px; display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                <div>
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-sub);">Remaining needed</div>
                    <div style="font-size: 15px; font-weight: 800; color: #b45309; letter-spacing: -0.01em;" class="tabular-num">₹{q_bonus['remaining']:,.0f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-sub);">Run-rate needed</div>
                    <div style="font-size: 11px; color: var(--text-muted);"><b class="tabular-num">₹{q_bonus['daily_runrate_needed']:,.0f}</b> / day</div>
                </div>
            </div>
        </div>
        """
    )

# 3. Annual Fee Waiver
annual = data["milestones"]["annual_waiver"]
with m_col3:
    ann_tag = "Waived" if annual["met"] else f"{annual['days_left']}d remaining"
    ann_class = "pill-green" if annual["met"] else "pill-blue"
    st.html(
        f"""
        <div class="metal-card" style="min-height: 236px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <div style="font-size: 12px; font-weight: 600; color: var(--text-muted);">Annual fee waiver</div>
                        <div style="font-size: 16px; font-weight: 700; color: var(--text-main);">Save ₹10,000 Fee</div>
                    </div>
                    <span class="pill {ann_class}">{ann_tag}</span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: #9a6014; margin: 6px 0;" class="tabular-num">
                    ₹{annual["spend"]:,.0f} <span style="font-size: 14px; font-weight: 500; color: var(--text-sub);">/ ₹{annual["target"]:,.0f}</span>
                    <span style="font-size: 13px; font-weight: 700; color: #9a6014; margin-left: 6px;">({annual['progress']}%)</span>
                </div>
                <div style="background: var(--progress-bg); border-radius: 999px; height: 8px; margin: 8px 0; overflow: hidden;">
                    <div style="background: #9a6014; width: {annual['progress']}%; height: 100%;"></div>
                </div>
            </div>
            <div style="background: var(--bg-subcard); border: 1px solid var(--border-default); border-radius: 10px; padding: 9px 12px; display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                <div>
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-sub);">Remaining to waive</div>
                    <div style="font-size: 15px; font-weight: 800; color: #9a6014; letter-spacing: -0.01em;" class="tabular-num">₹{annual['remaining']:,.0f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-sub);">Deadline</div>
                    <div style="font-size: 11px; color: var(--text-muted);"><b class="tabular-num">{annual['period_end']}</b> ({annual['days_left']}d left)</div>
                </div>
            </div>
        </div>
        """
    )

# ─── SECTION 3: INTERACTIVE TABS (HISTORY, LEDGER & REDEMPTIONS) ──────────────
tab_history, tab_ledger, tab_redemptions = st.tabs([
    "Monthly history & caps",
    "Live transactions",
    "Points redemptions",
])

with tab_history:
    st.markdown("##### Historical Monthly Reward Points & SmartBuy Cap Utilization")
    history = data.get("monthly_history", [])

    # Monthly Points Comparison Table
    if history:
        table_rows = []
        for h in history:
            table_rows.append({
                "Month": h["label"],
                "Total Spend": h["total_spend"],
                "Base RP": h["base_points"],
                "Accelerated RP": h["accelerated_points"],
                "Cap Utilization": min(h["accelerated_percent_used"], 100.0),
                "Headroom Left": h["accelerated_remaining"],
                "Total Points": h["total_points"],
                "Travel Value": h["realized_value_inr"],
                "SmartBuy Txs": f"{h['smartbuy_tx_count']} / {h['total_tx_count']}",
            })
        df_history = pd.DataFrame(table_rows)
        st.dataframe(
            df_history,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Month": st.column_config.TextColumn("Month", width="medium"),
                "Total Spend": st.column_config.NumberColumn("Total Spend", format="₹%d"),
                "Base RP": st.column_config.NumberColumn("Base RP", format="%d RP"),
                "Accelerated RP": st.column_config.NumberColumn("Accelerated RP", format="%d RP"),
                "Cap Utilization": st.column_config.ProgressColumn("10k Cap Used", min_value=0, max_value=100, format="%.1f%%"),
                "Headroom Left": st.column_config.NumberColumn("Cap Left", format="%d RP"),
                "Total Points": st.column_config.NumberColumn("Total Earned", format="%d RP"),
                "Travel Value": st.column_config.NumberColumn("SmartBuy Value", format="₹%d"),
                "SmartBuy Txs": st.column_config.TextColumn("SmartBuy Txs"),
            },
        )

    # Month Drilldown Expander
    st.html("<div style='height: 10px;'></div>")
    with st.expander("Itemized transactions by month"):
        month_choices = [h["label"] for h in history]
        # Default to current ongoing month (first entry in history)
        default_idx = 0 if month_choices else 0
        selected_month_label = st.selectbox("Select Month to Inspect:", month_choices, index=default_idx)
        selected_month_data = next((h for h in history if h["label"] == selected_month_label), None)
        if selected_month_data and selected_month_data["transactions"]:
            m_df = pd.DataFrame([
                {
                    "Date": t["date"],
                    "Merchant": t["merchant"],
                    "Category": f"{t['icon']} {t['category']}",
                    "Amount": t["amount"],
                    "Base RP": t["base_points"],
                    "Accelerated RP": t["raw_accelerated_points"],
                    "Total RP": t["base_points"] + t["raw_accelerated_points"],
                }
                for t in selected_month_data["transactions"]
            ])
            st.dataframe(
                m_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
                    "Base RP": st.column_config.NumberColumn("Base RP", format="%d RP"),
                    "Accelerated RP": st.column_config.NumberColumn("Accelerated RP", format="%d RP"),
                    "Total RP": st.column_config.NumberColumn("Total RP", format="%d RP"),
                },
            )

with tab_ledger:
    # Build dynamic filter choices
    dynamic_months = [h["label"] for h in history]
    primary_filters = ["All Transactions", "SmartBuy Accelerated Only", "Current Billing Cycle"]
    filter_options = primary_filters + [f"Month: {m}" for m in dynamic_months]

    # Available categories
    all_categories = sorted(list({t["category"] for t in data["transactions"]}))

    # Filter controls row
    f_row1, f_row2 = st.columns([1.2, 1.2])
    with f_row1:
        tx_filter = st.selectbox("Cycle / Period Filter", filter_options)
    with f_row2:
        selected_cats = st.multiselect("Filter Category", all_categories, default=[], placeholder="All categories")

    f_s1, f_s2 = st.columns([2.2, 0.8], vertical_alignment="bottom")
    with f_s1:
        search_query = st.text_input("Search merchant...", placeholder="e.g. Flight, Titan, Manyavar")

    tx_list = data["transactions"]
    if tx_filter == "SmartBuy Accelerated Only":
        tx_list = [t for t in tx_list if t["is_smartbuy"]]
    elif tx_filter == "Current Billing Cycle":
        b_start = datetime.date.fromisoformat(data["billing_cycle"]["start"])
        b_end = datetime.date.fromisoformat(data["billing_cycle"]["end"])
        tx_list = [t for t in tx_list if t["tx_date"] and b_start <= t["tx_date"] <= b_end]
    elif tx_filter.startswith("Month: "):
        m_label = tx_filter.replace("Month: ", "").strip()
        m_match = next((h for h in history if h["label"] == m_label), None)
        if m_match:
            prefix = f"{m_match['year']}-{m_match['month']:02d}"
            tx_list = [t for t in tx_list if t["date"].startswith(prefix)]

    if selected_cats:
        tx_list = [t for t in tx_list if t["category"] in selected_cats]

    if search_query:
        tx_list = [t for t in tx_list if search_query.lower() in t["merchant"].lower()]

    if tx_list:
        total_filtered_spend = sum(t["amount"] for t in tx_list)
        total_filtered_base = sum(t["base_points"] for t in tx_list)
        total_filtered_acc = sum(t["raw_accelerated_points"] for t in tx_list)
        total_filtered_rp = total_filtered_base + total_filtered_acc
        avg_rate = (total_filtered_rp / total_filtered_spend * 100) if total_filtered_spend > 0 else 0.0

        # Summary Metrics Chips
        st.html(
            f"""
            <div style="display: flex; gap: 12px; flex-wrap: wrap; margin: 12px 0 16px 0;">
                <div style="background: var(--bg-card); border: 1px solid var(--border-default); padding: 7px 14px; border-radius: 10px;">
                    <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Transactions:</span>
                    <span style="font-size: 14px; font-weight: 700; color: var(--text-main); margin-left: 6px;" class="tabular-num">{len(tx_list)}</span>
                </div>
                <div style="background: var(--bg-card); border: 1px solid var(--border-default); padding: 7px 14px; border-radius: 10px;">
                    <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Filtered spend:</span>
                    <span style="font-size: 14px; font-weight: 700; color: #9a6014; margin-left: 6px;" class="tabular-num">₹{total_filtered_spend:,.2f}</span>
                </div>
                <div style="background: var(--bg-card); border: 1px solid var(--border-default); padding: 7px 14px; border-radius: 10px;">
                    <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Base points:</span>
                    <span style="font-size: 14px; font-weight: 700; color: #784708; margin-left: 6px;" class="tabular-num">{total_filtered_base:,} RP</span>
                </div>
                <div style="background: var(--bg-card); border: 1px solid var(--border-default); padding: 7px 14px; border-radius: 10px;">
                    <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Accelerated points:</span>
                    <span style="font-size: 14px; font-weight: 700; color: #b45309; margin-left: 6px;" class="tabular-num">{total_filtered_acc:,} RP</span>
                </div>
                <div style="background: var(--bg-card); border: 1px solid var(--border-default); padding: 7px 14px; border-radius: 10px;">
                    <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Total points:</span>
                    <span style="font-size: 14px; font-weight: 700; color: #15803d; margin-left: 6px;" class="tabular-num">{total_filtered_rp:,} RP</span>
                </div>
            </div>
            """
        )

        ledger_data = [
            {
                "Date": t["date"],
                "Merchant": t["merchant"],
                "Category": f"{t['icon']} {t['category']}",
                "Amount": t["amount"],
                "Base RP": t["base_points"],
                "Accelerated RP": t["raw_accelerated_points"],
                "Total RP": t["base_points"] + t["raw_accelerated_points"],
                "Reward Rate %": round(t["total_multiplier"] * 3.33, 1),
            }
            for t in tx_list
        ]
        df = pd.DataFrame(ledger_data)
        
        with f_s2:
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Export CSV",
                data=csv_data,
                file_name=f"dcbm_transactions_{datetime.date.today().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
                "Base RP": st.column_config.NumberColumn("Base RP", format="%d RP"),
                "Accelerated RP": st.column_config.NumberColumn("Accelerated RP", format="%d RP"),
                "Total RP": st.column_config.NumberColumn("Total RP", format="%d RP"),
                "Reward Rate %": st.column_config.ProgressColumn("Reward Rate", min_value=0, max_value=35, format="%.1f%%"),
            },
        )
    else:
        st.info("No transactions found matching the selected filter.")

with tab_redemptions:
    st.markdown("##### SmartBuy Reward Points Redemptions History")
    redemptions_list = data.get("redemptions", [])
    red_summary = data.get("redemptions_summary", {})

    total_pts_burned = sum(r.get("points_redeemed", 0) for r in redemptions_list)
    total_fare = sum(r.get("total_fare", 0.0) for r in redemptions_list)
    total_saved = sum(r.get("value_saved_inr", 0.0) for r in redemptions_list)
    total_cash = sum(r.get("cash_paid", 0.0) for r in redemptions_list)

    st.html(
        f"""
        <div style="background: var(--bg-subcard); border: 1px solid var(--border-default); border-radius: 12px; padding: 14px 20px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Points redeemed:</span>
                <span style="font-size: 16px; font-weight: 700; color: #b45309; margin-left: 6px;" class="tabular-num">{total_pts_burned:,} RP</span>
            </div>
            <div>
                <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Direct savings:</span>
                <span style="font-size: 16px; font-weight: 700; color: #15803d; margin-left: 6px;" class="tabular-num">₹{total_saved:,.0f}</span>
            </div>
            <div>
                <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Booking value:</span>
                <span style="font-size: 16px; font-weight: 700; color: var(--text-main); margin-left: 6px;" class="tabular-num">₹{total_fare:,.0f}</span>
            </div>
            <div>
                <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Cash paid (card):</span>
                <span style="font-size: 16px; font-weight: 700; color: #9a6014; margin-left: 6px;" class="tabular-num">₹{total_cash:,.0f}</span>
            </div>
        </div>
        """
    )

    if redemptions_list:
        red_rows = []
        for r in redemptions_list:
            red_rows.append({
                "Date": r["date"],
                "Category": r["type"],
                "Description": r["description"],
                "Order Reference": r["order_reference"],
                "Points Burned": r["points_redeemed"],
                "Cash Paid": r["cash_paid"],
                "Total Fare": r["total_fare"],
                "Value Saved": r["value_saved_inr"],
                "Rate": f"₹{r['redemption_rate']:.2f}/pt",
            })
        df_red = pd.DataFrame(red_rows)
        st.dataframe(
            df_red,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date": st.column_config.TextColumn("Date", width="small"),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "Description": st.column_config.TextColumn("Booking Description", width="medium"),
                "Order Reference": st.column_config.TextColumn("Order Reference #", width="medium"),
                "Points Burned": st.column_config.NumberColumn("Points Burned", format="%d RP"),
                "Cash Paid": st.column_config.NumberColumn("Cash Paid (DCBM)", format="₹%d"),
                "Total Fare": st.column_config.NumberColumn("Total Booking Value", format="₹%d"),
                "Value Saved": st.column_config.NumberColumn("Value Saved", format="₹%d"),
                "Rate": st.column_config.TextColumn("Redemption Rate", width="small"),
            },
        )
    else:
        st.info("No reward points redemptions found in synced Gmail messages.")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.html(
    f"""
    <div style="text-align: center; font-size: 12px; color: {T['footer_text']}; margin-top: 30px; border-top: 1px solid {T['footer_border']}; padding-top: 15px;">
        HDFC Diners Club Black Metal Dashboard • Automated via Gmail Alerts • Built for Ejaz Anwar
    </div>
    """
)
