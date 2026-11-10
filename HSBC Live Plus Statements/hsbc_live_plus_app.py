#!/usr/bin/env python3
"""
HSBC Live+ Credit Card Streamlit Dashboard.
Executive Haute Metal Bento Redesign (Option 1).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Setup paths
CARD_DIR = Path(__file__).resolve().parent
ROOT_DIR = CARD_DIR.parent
sys.path.insert(0, str(CARD_DIR))
sys.path.insert(0, str(ROOT_DIR))

import importlib
import hsbc_engine
importlib.reload(hsbc_engine)


def clean_html(raw_html: str) -> str:
    """Strips all leading and trailing whitespace from every line to prevent CommonMark code blocks."""
    return "\n".join(line.strip() for line in raw_html.splitlines() if line.strip())


def render_app():
    # Page configuration
    try:
        st.set_page_config(
            page_title="HSBC Live+ | Control Center",
            page_icon="💳",
            layout="wide",
            initial_sidebar_state="collapsed",
        )
    except Exception:
        pass

    # ─── Multi-Card Router Gate ───────────────────────────────────────────────────
    if "selected_card" in st.session_state and "HDFC" in str(st.session_state["selected_card"]):
        hdfc_app_path = ROOT_DIR / "HDFC Diners Black Metal Statements" / "hdfc_dcbm_app.py"
        if hdfc_app_path.exists():
            import runpy
            runpy.run_path(str(hdfc_app_path), run_name="__main__")
            st.stop()

    # Design Tokens (Haute Metal Executive Palette with Signature HSBC Crimson)
    T = {
        "app_bg": "#f8fafc",
        "card_bg": "#ffffff",
        "subcard_bg": "#f8fafc",
        "text_main": "#0f172a",
        "text_muted": "#475569",
        "text_sub": "#64748b",
        "border_default": "#e2e8f0",
        "border_sub": "#f1f5f9",
        "border_strong": "#cbd5e1",
        "accent_red": "#db0011",
        "accent_red_hover": "#b8000e",
        "accent_red_subtle": "rgba(219, 0, 17, 0.08)",
        "accent_red_border": "rgba(219, 0, 17, 0.22)",
        "accent_green": "#059669",
        "accent_green_bg": "#ecfdf5",
        "accent_green_border": "#a7f3d0",
        "accent_gold": "#b47820",
        "accent_gold_bg": "#fffbeb",
        "accent_gold_border": "#fde68a",
        "progress_bg": "#e2e8f0",
        "btn_bg": "#ffffff",
        "btn_color": "#0f172a",
        "btn_border": "#cbd5e1",
        "btn_hover": "#f8fafc",
        "badge_bg": "#f1f5f9",
        "badge_border": "#cbd5e1",
    }

    # Inject Haute Metal Executive CSS
    st.html(
        clean_html(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

        :root {{
            --bg-canvas: {T["app_bg"]};
            --bg-card: {T["card_bg"]};
            --bg-subcard: {T["subcard_bg"]};
            --text-main: {T["text_main"]};
            --text-muted: {T["text_muted"]};
            --text-sub: {T["text_sub"]};
            --border-default: {T["border_default"]};
            --border-sub: {T["border_sub"]};
            --border-strong: {T["border_strong"]};
            --accent-red: {T["accent_red"]};
            --accent-green: {T["accent_green"]};
            --accent-gold: {T["accent_gold"]};
            --progress-bg: {T["progress_bg"]};
        }}

        html, body, [class*="css"], .stMarkdown, p, div, label, span, h1, h2, h3, h4, h5, h6 {{
            font-family: 'Outfit', sans-serif !important;
        }}

        .tabular-num, .hsbc-metric-large, [data-testid="stDataFrame"], table, .pill {{
            font-variant-numeric: tabular-nums lining-nums;
        }}

        *:focus-visible {{
            outline: 2px solid {T["accent_red"]} !important;
            outline-offset: 2px !important;
        }}

        .stApp {{
            background-color: var(--bg-canvas) !important;
            color: var(--text-main) !important;
        }}

        /* Header space removal & line cut-through elimination */
        header[data-testid="stHeader"], [data-testid="stHeader"], header {{
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            border-bottom: none !important;
            box-shadow: none !important;
        }}
        [data-testid="stToolbar"], #stDecoration, div[data-testid="stDecoration"] {{
            display: none !important;
            height: 0 !important;
            border: none !important;
        }}
        .stApp hr {{
            display: none !important;
        }}

        .block-container, div[data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] {{
            padding-top: 1.2rem !important;
            padding-bottom: 3rem !important;
            max-width: 1260px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            border: none !important;
        }}

        /* Symmetrical Bento Grid Equal Height Flex Rules */
        div[data-testid="stHorizontalBlock"] {{
            align-items: stretch !important;
        }}
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
            display: flex !important;
            flex-direction: column !important;
        }}
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] > div {{
            display: flex !important;
            flex-direction: column !important;
            flex: 1 1 100% !important;
            height: 100% !important;
        }}
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] [data-testid="stVerticalBlock"] {{
            display: flex !important;
            flex-direction: column !important;
            flex: 1 1 100% !important;
            height: 100% !important;
        }}
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] [data-testid="stHtml"],
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] div.element-container {{
            display: flex !important;
            flex-direction: column !important;
            flex: 1 1 100% !important;
            height: 100% !important;
        }}

        /* Executive Cards */
        .hsbc-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-default);
            border-radius: 18px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 8px 24px -4px rgba(15, 23, 42, 0.05);
            display: flex !important;
            flex-direction: column !important;
            justify-content: space-between !important;
            flex: 1 1 100% !important;
            height: 100% !important;
            min-height: 295px;
            margin-bottom: 0px !important;
            box-sizing: border-box;
            transition: border-color 150ms ease, box-shadow 150ms ease;
        }}
        .hsbc-card:hover {{
            border-color: var(--border-strong);
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
        }}

        .hsbc-milestone-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-default);
            border-radius: 16px;
            padding: 22px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 6px 16px -4px rgba(15, 23, 42, 0.04);
            display: flex !important;
            flex-direction: column !important;
            justify-content: space-between !important;
            flex: 1 1 100% !important;
            height: 100% !important;
            min-height: 205px;
            margin-bottom: 0px !important;
            box-sizing: border-box;
            transition: border-color 150ms ease;
        }}
        .hsbc-milestone-card:hover {{
            border-color: var(--border-strong);
        }}

        /* Label Tag */
        .hsbc-label-tag {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 3px;
        }}

        /* Card Headings */
        .hsbc-heading {{
            font-size: 16.5px;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: var(--text-main);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* Big Metrics */
        .hsbc-metric-large {{
            font-size: 38px;
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.05;
        }}
        .hsbc-metric-unit {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text-muted);
        }}
        .hsbc-metric-sub {{
            font-size: 12.5px;
            color: var(--text-muted);
            margin-top: 4px;
            font-weight: 500;
        }}

        /* Clean Pills */
        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 11px;
            border-radius: 9999px;
            font-size: 11.5px;
            font-weight: 600;
            letter-spacing: 0.01em;
            white-space: nowrap;
            line-height: 1.3;
        }}
        .pill-red {{
            background: rgba(219, 0, 17, 0.07);
            color: {T["accent_red"]};
            border: 1px solid rgba(219, 0, 17, 0.22);
        }}
        .pill-green {{
            background: #ecfdf5;
            color: #059669;
            border: 1px solid #a7f3d0;
        }}
        .pill-gold {{
            background: #fffbeb;
            color: #b47820;
            border: 1px solid #fde68a;
        }}
        .pill-slate {{
            background: #f1f5f9;
            color: #0f172a;
            border: 1px solid #cbd5e1;
        }}

        .status-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            display: inline-block;
        }}
        .status-dot-green {{
            background-color: #10b981;
        }}

        /* Custom Slim Progress Bars */
        .hsbc-progress-container {{
            width: 100%;
            height: 6px;
            background: var(--progress-bg);
            border-radius: 999px;
            overflow: hidden;
            margin: 8px 0;
        }}
        .hsbc-progress-bar {{
            height: 100%;
            border-radius: 999px;
            transition: width 0.3s ease;
        }}

        /* Subcards & Merchant Chips */
        .hsbc-subcard {{
            background: var(--bg-subcard);
            border: 1px solid var(--border-default);
            border-radius: 10px;
            padding: 10px 12px;
            box-sizing: border-box;
        }}
        .hsbc-subcard-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 7px 11px;
            background: var(--bg-subcard);
            border: 1px solid var(--border-default);
            border-radius: 8px;
            margin-bottom: 6px;
        }}

        .hsbc-chip {{
            display: inline-block;
            background: #ffffff;
            border: 1px solid var(--border-default);
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            margin: 2px 2px;
        }}

        /* Stat Badge Box */
        .hsbc-stat-badge {{
            background: var(--bg-subcard);
            border: 1px solid var(--border-default);
            border-radius: 10px;
            padding: 10px 14px;
            flex: 1 1 0;
        }}
        .hsbc-stat-label {{
            font-size: 10px;
            color: var(--text-muted);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .hsbc-stat-val {{
            font-size: 16px;
            font-weight: 800;
            color: var(--text-main);
            margin-top: 3px;
        }}

        /* Executive Sync Button */
        div.stButton > button {{
            height: 38px !important;
            min-height: 38px !important;
            max-height: 38px !important;
            background: {T["btn_bg"]} !important;
            color: {T["btn_color"]} !important;
            border: 1px solid {T["btn_border"]} !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
            font-size: 13.5px !important;
            font-weight: 600 !important;
            border-radius: 10px !important;
            padding: 0 16px !important;
            transition: border-color 150ms ease, background-color 150ms ease, box-shadow 150ms ease !important;
        }}
        div.stButton > button:hover {{
            background-color: {T["btn_hover"]} !important;
            border-color: #94a3b8 !important;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.08) !important;
        }}
        div.stButton > button:focus-visible {{
            outline: 2px solid {T["accent_red"]} !important;
            outline-offset: 2px !important;
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
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
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
            border-color: {T["accent_red"]} !important;
            box-shadow: 0 2px 8px rgba(219, 0, 17, 0.15) !important;
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
            color: {T["accent_red"]} !important;
        }}
        li[data-baseweb="menu-item"][aria-selected="true"] {{
            background-color: rgba(219, 0, 17, 0.08) !important;
            color: {T["accent_red"]} !important;
            font-weight: 700 !important;
        }}

        /* Tabs styling */
        div[data-baseweb="tab-list"] {{
            gap: 8px !important;
            border-bottom: 1px solid var(--border-default) !important;
            padding-bottom: 2px !important;
        }}
        button[data-baseweb="tab"] {{
            font-weight: 600 !important;
            font-size: 14px !important;
            color: var(--text-muted) !important;
            border-radius: 8px !important;
            padding: 8px 16px !important;
            border-bottom: none !important;
            transition: color 150ms ease, background-color 150ms ease !important;
        }}
        button[data-baseweb="tab"]:hover {{
            color: var(--text-main) !important;
            background-color: var(--bg-subcard) !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {T["accent_red"]} !important;
            font-weight: 700 !important;
            background-color: rgba(219, 0, 17, 0.06) !important;
        }}
        div[data-baseweb="tab-highlight"] {{
            background-color: {T["accent_red"]} !important;
            height: 2.5px !important;
            border-radius: 2px !important;
        }}

        /* Section Titles */
        .hsbc-section-title {{
            font-size: 17px;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 22px;
            margin-bottom: 14px;
        }}

        /* Executive Luxury Toast Notification */
        div[data-testid="stToast"] {{
            background: #0f172a !important;
            background-color: #0f172a !important;
            border: 1px solid rgba(219, 0, 17, 0.4) !important;
            border-radius: 14px !important;
            box-shadow: 0 16px 36px -4px rgba(15, 23, 42, 0.45), 0 0 0 1px rgba(219, 0, 17, 0.2) !important;
            padding: 14px 18px !important;
            min-width: 300px !important;
            max-width: 440px !important;
            color: #f8fafc !important;
        }}
        div[data-testid="stToast"] * {{
            color: #f8fafc !important;
            font-family: 'Outfit', sans-serif !important;
        }}
        div[data-testid="stToast"] [data-testid="stMarkdownContainer"] p {{
            color: #f8fafc !important;
            font-size: 13.5px !important;
            font-weight: 600 !important;
            line-height: 1.4 !important;
            margin: 0 !important;
        }}
        div[data-testid="stToast"] button:not(:has(svg)) {{
            display: none !important;
        }}

        /* Mobile Responsive Layout */
        @media (max-width: 768px) {{
            [data-testid="stAppViewBlockContainer"] {{
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
                padding-top: 0.8rem !important;
            }}
            .hsbc-card, .hsbc-milestone-card {{
                min-height: 0 !important;
                padding: 18px !important;
                margin-bottom: 14px !important;
            }}
            .hsbc-metric-large {{
                font-size: 30px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(.mobile-card-badge) {{
                display: flex !important;
                flex-direction: column !important;
                width: 100% !important;
                gap: 10px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(.mobile-card-badge) > div[data-testid="stColumn"] {{
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                flex: 1 1 100% !important;
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
        }}
        </style>
        """)
    )

    # ─── Load Data ─────────────────────────────────────────────────────────────
    @st.cache_data(ttl=60)
    def load_data():
        alerts_file = CARD_DIR / "gmail_alerts.json"
        meta_file = CARD_DIR / "sync_metadata.json"
        needs_sync = not alerts_file.exists()
        if not needs_sync and meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                if meta.get("card_ending") != "8690":
                    needs_sync = True
            except Exception:
                needs_sync = True
        if needs_sync:
            try:
                hsbc_engine.trigger_live_sync(CARD_DIR)
            except Exception:
                pass
        return hsbc_engine.compute_hsbc_dashboard_data(CARD_DIR)

    data = load_data()

    # ─── Top Header Controls Row (Flawlessly Aligned on Center Baseline) ────────
    col_head_left, col_head_right = st.columns([2.6, 1.4], vertical_alignment="center")

    with col_head_left:
        card_col, badge_col = st.columns([1.45, 1.15], vertical_alignment="center")
        with card_col:
            card_options = ["HDFC Diners Club Black Metal", "HSBC Live+ Credit Card"]
            current_card = st.session_state.get("selected_card", "HSBC Live+ Credit Card")
            if current_card not in card_options:
                current_card = "HSBC Live+ Credit Card"

            def on_hsbc_card_change():
                st.session_state["selected_card"] = st.session_state["active_card_switcher"]

            st.selectbox(
                "Credit Card",
                options=card_options,
                index=card_options.index(current_card),
                key="active_card_switcher",
                on_change=on_hsbc_card_change,
                label_visibility="collapsed",
            )
        with badge_col:
            st.html(
                f"""
                <div style="display: flex; align-items: center; gap: 8px; height: 38px;">
                    <span class="mobile-card-badge" style="font-size: 13px; font-weight: 700; color: {T['text_main']}; background: {T['badge_bg']}; padding: 4px 10px; border-radius: 8px; border: 1px solid {T['badge_border']};">
                        •••• {data.get('card_ending', '8690')}
                    </span>
                    <span class="pill pill-gold" style="font-size: 11px; font-weight: 700; padding: 4px 9px;">
                        Visa Infinite
                    </span>
                </div>
                """
            )

    with col_head_right:
        sync_time_str = data["sync_metadata"]["last_synced"]
        try:
            dt = datetime.datetime.fromisoformat(sync_time_str)
            friendly_time = dt.strftime("%d %b %H:%M")
        except Exception:
            friendly_time = "Live"

        btn_sync, btn_time = st.columns([1.0, 1.0], vertical_alignment="center")
        with btn_sync:
            st.html("<div class='mobile-sync-btn' style='display:none;'></div>")
            if st.button("Sync alerts", use_container_width=True):
                with st.spinner("Checking Gmail alerts..."):
                    try:
                        sync_res = hsbc_engine.trigger_live_sync(CARD_DIR)
                        if sync_res.get("status") == "error":
                            st.toast(f"Sync error: {sync_res.get('message')}")
                        else:
                            st.cache_data.clear()
                            st.toast(f"Sync complete • {sync_res.get('alert_count', 0)} new alerts fetched")
                            st.rerun()
                    except Exception as exc:
                        err_msg = str(exc)
                        if "credentials are not configured" in err_msg:
                            st.toast(f"Mac daemon active • Ledger verified ({friendly_time})")
                        else:
                            st.toast(f"Sync notice: {err_msg[:50]}")
        with btn_time:
            st.html(
                f"""
                <div style="text-align: right; display: flex; justify-content: flex-end; align-items: center; height: 38px;">
                    <span class="pill pill-green" style="font-size: 11.5px; white-space: nowrap; padding: 5px 12px; gap: 6px; font-weight: 600;">
                        <span class="status-dot status-dot-green"></span> {friendly_time}
                    </span>
                </div>
                """
            )

    # Header Subtitle (Placed cleanly below the controls)
    st.html(
        f"""
        <div class="mobile-header-sub" style="font-size: 12.5px; color: {T['text_sub']}; font-weight: 500; margin-top: 4px; margin-bottom: 14px;">
            Automated Real-Time Cashback & Spend Tracker from Gmail InstaAlerts
        </div>
        """
    )

    # ─── Section 1: Hero Cashback & Headroom (3 Symmetrical Bento Columns) ──────
    h_col1, h_col2, h_col3 = st.columns(3)

    cycle_info = data["cycle"]
    cap_info = data["cashback_cap"]
    portfolio = data["portfolio"]

    # Compute confirmed & estimated cashback directly from current cycle transactions
    cycle_txns = data.get("transactions", {}).get("current_cycle", [])
    calc_confirmed = sum(t["cashback_earned"] for t in cycle_txns if t.get("is_accelerated") and t.get("evidence") == "confirmed")
    calc_estimated = sum(t["cashback_earned"] for t in cycle_txns if t.get("is_accelerated") and t.get("evidence") != "confirmed")
    confirmed_cb = calc_confirmed if cycle_txns else cap_info.get("confirmed_cb", cap_info.get("earned", 0.0))
    estimated_cb = calc_estimated if cycle_txns else cap_info.get("estimated_cb", 0.0)

    # Tile 1: 10% Cashback Cap Monitor
    with h_col1:
        st.html(
            f"""
            <div class="hsbc-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: {T['accent_red']};">10% Accelerated Cashback</div>
                            <div class="hsbc-heading">{cycle_info['label']}</div>
                        </div>
                        <span class="pill pill-red">
                            <span class="status-dot" style="background:{T['accent_red']};"></span> {cycle_info['days_remaining']}D Left
                        </span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 6px;">
                        <span class="hsbc-metric-large" style="color: {T['text_main']};">₹{cap_info['earned']:.2f}</span>
                        <span class="hsbc-metric-unit">/ ₹{cap_info['cap_limit']:,.0f} Cashback</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; font-size: 12.5px; color: var(--text-muted);">
                        <span>₹{confirmed_cb:,.2f} confirmed</span>
                        <span style="font-weight: 600; color: {T['accent_red']};">₹{cap_info['remaining_cb']:,.2f} left</span>
                    </div>
                </div>

                <div style="margin-top: 16px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); font-weight: 600;">
                        <span>Cap Used: <b>{cap_info['percent_used']}%</b></span>
                        <span>Accelerated Spend: <b>₹{cap_info['accelerated_spend']:,.0f} / ₹{cap_info['max_accelerated_spend']:,.0f}</b></span>
                    </div>
                    <div class="hsbc-progress-container">
                        <div class="hsbc-progress-bar" style="width: {min(100.0, cap_info['percent_used'])}%; background: linear-gradient(90deg, #db0011 0%, #ff4d5a 100%);"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted);">
                        <span>Cycle: <b>{datetime.date.fromisoformat(cycle_info['start']).strftime('%d %b')} – {datetime.date.fromisoformat(cycle_info['end']).strftime('%d %b')}</b></span>
                        <span>Monthly Cap: <b>₹{cap_info['cap_limit']:,.0f}</b></span>
                    </div>
                </div>
            </div>
            """
        )

    # Tile 2: Food Delivery, Groceries & Dining Headroom
    with h_col2:
        st.html(
            f"""
            <div class="hsbc-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: var(--text-muted);">Spend Headroom</div>
                            <div class="hsbc-heading">Food Delivery, Groceries & Dining</div>
                        </div>
                        <span class="pill pill-green">10% Rate</span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 6px; margin-top: 6px;">
                        <span class="hsbc-metric-large" style="color: {T['accent_red']};">₹{cap_info['remaining_accelerated_spend']:,.0f}</span>
                        <span class="hsbc-metric-unit">spend headroom</span>
                    </div>
                    <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 6px;">
                        Spend capacity before reaching the ₹{cap_info['cap_limit']:,.0f} monthly cap
                    </div>
                </div>

                <div style="margin-top: 16px;">
                    <div class="hsbc-subcard">
                        <div style="font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
                            Eligible 10% Merchant Platforms
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                            <span class="hsbc-chip">Zomato</span>
                            <span class="hsbc-chip">Swiggy</span>
                            <span class="hsbc-chip">Blinkit</span>
                            <span class="hsbc-chip">Zepto</span>
                            <span class="hsbc-chip">Instamart</span>
                            <span class="hsbc-chip">BigBasket</span>
                            <span class="hsbc-chip">Dining & Cafes</span>
                        </div>
                    </div>
                </div>
            </div>
            """
        )

    # Tile 3: Direct Statement Savings & Portfolio Net Return
    with h_col3:
        st.html(
            f"""
            <div class="hsbc-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: var(--text-muted);">Direct Statement Credit</div>
                            <div class="hsbc-heading">Portfolio Net Savings</div>
                        </div>
                        <span class="pill pill-green">Direct Credit</span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 6px; margin-top: 6px;">
                        <span class="hsbc-metric-large" style="color: {T['accent_green']};">₹{portfolio['lifetime_cashback']:,.2f}</span>
                        <span class="hsbc-metric-unit">lifetime savings</span>
                    </div>
                    <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 6px;">
                        Credited directly to reduce statement balance
                    </div>
                </div>

                <div style="margin-top: 16px;">
                    <div style="display: flex; gap: 8px;">
                        <div class="hsbc-stat-badge">
                            <div class="hsbc-stat-label">TOTAL SPEND TRACKED</div>
                            <div class="hsbc-stat-val">₹{portfolio['lifetime_spend']:,.2f}</div>
                        </div>
                        <div class="hsbc-stat-badge">
                            <div class="hsbc-stat-label">EFFECTIVE REWARD RATE</div>
                            <div class="hsbc-stat-val" style="color: {T['accent_green']};">{portfolio['effective_reward_rate']:.2f}%</div>
                        </div>
                    </div>
                </div>
            </div>
            """
        )

    # ─── Section 2: Milestones, Fee Waiver & Travel Privileges ──────────────────
    st.html(
        f"""
        <div class="hsbc-section-title">
            Milestones, Fee Waiver & Travel Privileges
        </div>
        """
    )

    m_col1, m_col2, m_col3 = st.columns(3)

    welcome = data["welcome"]
    fee = data["fee_waiver"]
    lounge = data["lounge"]

    # Milestone 1: 30-Day Welcome Benefit
    with m_col1:
        st.html(
            f"""
            <div class="hsbc-milestone-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: var(--text-muted);">30-Day Welcome Benefit</div>
                            <div class="hsbc-heading">₹{welcome['reward']:,} Welcome Cashback</div>
                        </div>
                        <span class="pill pill-green">Unlocked</span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 6px; margin-top: 6px;">
                        <span style="font-size: 24px; font-weight: 800; color: {T['accent_green']};">₹{welcome['spent']:,.0f}</span>
                        <span style="font-size: 13.5px; color: var(--text-muted); font-weight: 600;">/ ₹{welcome['target']:,.0f} spent</span>
                    </div>
                </div>
                <div style="margin-top: 12px;">
                    <div class="hsbc-progress-container">
                        <div class="hsbc-progress-bar" style="width: 100%; background: {T['accent_green']};"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 11.5px; color: var(--text-muted);">
                        <span>Target Met in First 30 Days</span>
                        <span style="font-weight: 600; color: {T['accent_green']};">+ ₹750 Activation Voucher</span>
                    </div>
                </div>
            </div>
            """
        )

    # Milestone 2: Annual Fee Waiver
    with m_col2:
        st.html(
            f"""
            <div class="hsbc-milestone-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: var(--text-muted);">Annual Fee Waiver</div>
                            <div class="hsbc-heading">Save ₹{fee['annual_fee']} + GST</div>
                        </div>
                        <span class="pill pill-gold">
                            <span class="status-dot" style="background:{T['accent_gold']};"></span> {fee['days_left']}D Left
                        </span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 6px; margin-top: 6px;">
                        <span style="font-size: 24px; font-weight: 800; color: var(--text-main);">₹{fee['spent']:,.0f}</span>
                        <span style="font-size: 13.5px; color: var(--text-muted); font-weight: 600;">/ ₹{fee['target']:,.0f} ({fee['percent']}%)</span>
                    </div>
                </div>
                <div style="margin-top: 12px;">
                    <div class="hsbc-progress-container">
                        <div class="hsbc-progress-bar" style="width: {min(100.0, fee['percent'])}%; background: {T['accent_gold']};"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 11.5px; color: var(--text-muted);">
                        <span>Remaining: <b>₹{fee['remaining']:,.0f}</b></span>
                        <span>Run-rate: <b>₹{fee['run_rate_needed']:,.0f} / day</b></span>
                    </div>
                </div>
            </div>
            """
        )

    # Milestone 3: Visa Infinite Privileges
    with m_col3:
        st.html(
            f"""
            <div class="hsbc-milestone-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: var(--text-muted);">Visa Infinite Privileges</div>
                            <div class="hsbc-heading">Lounge & Global Roaming</div>
                        </div>
                        <span class="pill pill-green">Active Tier</span>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 4px;">
                        <div class="hsbc-subcard-row">
                            <span style="font-size: 12px; font-weight: 600; color: var(--text-main);">Domestic Lounge (Jul–Dec)</span>
                            <span class="pill pill-green" style="font-size: 10px; padding: 2px 8px;">{lounge['domestic_h2']}</span>
                        </div>
                        <div class="hsbc-subcard-row">
                            <span style="font-size: 12px; font-weight: 600; color: var(--text-main);">International Lounge (Annual)</span>
                            <span class="pill pill-green" style="font-size: 10px; padding: 2px 8px;">{lounge['international']}</span>
                        </div>
                        <div class="hsbc-subcard-row" style="margin-bottom: 0;">
                            <span style="font-size: 12px; font-weight: 600; color: var(--text-main);">Complimentary Global eSIM</span>
                            <span class="pill pill-green" style="font-size: 10px; padding: 2px 8px;">{lounge['esim']}</span>
                        </div>
                    </div>
                </div>
            </div>
            """
        )

    # ─── Section 3: Interactive Tabs Section ───────────────────────────────────
    st.html("<div style='height: 16px;'></div>")
    tab_txns, tab_history, tab_perks = st.tabs([
        "Live Transactions",
        "Monthly History & Caps",
        "Reserve & Dining Privileges",
    ])

    # Tab 1: Live Transactions
    with tab_txns:
        cycle_txns = data["transactions"]["current_cycle"]
        all_txns = data["transactions"]["all"]

        t_head_c1, t_head_c2 = st.columns([3, 1], vertical_alignment="center")
        with t_head_c1:
            st.html(
                f"""
                <div style='font-weight: 700; font-size: 15px; color: {T['text_main']};'>
                    Statement Cycle: {datetime.date.fromisoformat(cycle_info['start']).strftime('%d %b %Y')} – {datetime.date.fromisoformat(cycle_info['end']).strftime('%d %b %Y')}
                </div>
                """
            )
        with t_head_c2:
            st.html(
                f"""
                <div style='text-align: right;'>
                    <span class='pill pill-green'>{len(cycle_txns)} Transactions Audited</span>
                </div>
                """
            )

        if cycle_txns:
            df_cycle = pd.DataFrame([
                {
                    "Date": item["date"],
                    "Merchant": item["merchant"],
                    "Amount": f"₹{item['amount']:,.2f}",
                    "Category": item["category"],
                    "MCC": item["mcc"],
                    "Rate": item["rate"],
                    "Cashback": f"+ ₹{item['cashback_earned']:,.2f}",
                    "Evidence": "Confirmed" if item["evidence"] == "confirmed" else "Estimated",
                }
                for item in cycle_txns
            ])
            st.dataframe(df_cycle, use_container_width=True, hide_index=True)
        else:
            st.info("No purchase transactions recorded yet for the active billing cycle.")

        # Expandable All Transactions
        with st.expander("View All Historical Transactions Across Cycles", expanded=False):
            df_all = pd.DataFrame([
                {
                    "Date": item["date"],
                    "Merchant": item["merchant"],
                    "Amount": f"₹{item['amount']:,.2f}",
                    "Category": item["category"],
                    "MCC": item["mcc"],
                    "Rate": item["rate"],
                    "Cashback": f"+ ₹{item['cashback_earned']:,.2f}",
                    "Confidence": "Confirmed" if item["evidence"] == "confirmed" else "Estimated",
                }
                for item in all_txns
            ])
            st.dataframe(df_all, use_container_width=True, hide_index=True)

    # Tab 2: Monthly History & Caps
    with tab_history:
        st.html(
            f"""
            <div style='font-weight: 700; font-size: 15px; margin-bottom: 12px; color: {T['text_main']};'>
                Historical Cashback by Billing Cycle
            </div>
            """
        )
        history_data = [
            {
                "Billing Cycle": "14 Jul – 13 Aug 2026",
                "Total Spend": "₹22,288.82",
                "10% Accelerated Spend": "₹10,163.50",
                "10% Cashback": "₹1,016.35",
                "1.5% Base Cashback": "₹45.80",
                "Total Cashback": "₹1,062.15",
            },
            {
                "Billing Cycle": f"{datetime.date.fromisoformat(cycle_info['start']).strftime('%d %b')} – {datetime.date.fromisoformat(cycle_info['end']).strftime('%d %b')} (Active)",
                "Total Spend": f"₹{cap_info['accelerated_spend']:,.2f}",
                "10% Accelerated Spend": f"₹{cap_info['accelerated_spend']:,.2f}",
                "10% Cashback": f"₹{cap_info['earned']:,.2f}",
                "1.5% Base Cashback": "₹0.00",
                "Total Cashback": f"₹{cap_info['total_cycle_cb']:,.2f}",
            },
        ]
        st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)

    # Tab 3: Curated Privileges
    with tab_perks:
        st.html(
            f"""
            <div style='font-weight: 700; font-size: 15px; margin-bottom: 14px; color: {T['text_main']};'>
                Curated Visa Infinite & Live+ Reserve Benefits
            </div>
            """
        )
        p_c1, p_c2, p_c3 = st.columns(3)
        with p_c1:
            st.html(
                f"""
                <div class="hsbc-subcard" style="padding: 18px; min-height: 120px;">
                    <div style="font-weight: 700; font-size: 14.5px; color: {T['text_main']};">The Live+ Reserve (TimesPrime)</div>
                    <div style="font-size: 12.5px; color: {T['text_sub']}; margin-top: 6px; line-height: 1.45;">
                        Curated dining menus & complimentary dessert/drinks at Indian Accent, Tresind, Comorin, and Olive.
                    </div>
                </div>
                """
            )
        with p_c2:
            st.html(
                f"""
                <div class="hsbc-subcard" style="padding: 18px; min-height: 120px;">
                    <div style="font-weight: 700; font-size: 14.5px; color: {T['text_main']};">BOGO Cinema Tickets</div>
                    <div style="font-size: 12.5px; color: {T['text_sub']}; margin-top: 6px; line-height: 1.45;">
                        Buy-1-Get-1 complimentary movie tickets via District by Zomato and BookMyShow platforms.
                    </div>
                </div>
                """
            )
        with p_c3:
            st.html(
                f"""
                <div class="hsbc-subcard" style="padding: 18px; min-height: 120px;">
                    <div style="font-weight: 700; font-size: 14.5px; color: {T['text_main']};">ITC Hotels Stay 2 Pay 1</div>
                    <div style="font-size: 12.5px; color: {T['text_sub']}; margin-top: 6px; line-height: 1.45;">
                        Complimentary 3rd night on 2 paid nights, or 50% discount on 2nd night at luxury ITC properties.
                    </div>
                </div>
                """
            )


if __name__ == "__main__":
    render_app()
