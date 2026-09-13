#!/usr/bin/env python3
"""
HSBC Live+ Credit Card Streamlit Dashboard.
Faithful implementation of approved V5 prototype.
"""

from __future__ import annotations

import datetime
from pathlib import Path
import sys
import textwrap

import pandas as pd
import streamlit as st

# Setup paths
CARD_DIR = Path(__file__).resolve().parent
ROOT_DIR = CARD_DIR.parent
sys.path.insert(0, str(CARD_DIR))
sys.path.insert(0, str(ROOT_DIR))

import hsbc_engine


def clean_html(raw_html: str) -> str:
    """Strips all leading and trailing whitespace from every line to prevent CommonMark code blocks."""
    return "\n".join(line.strip() for line in raw_html.splitlines() if line.strip())


def render_app():
    # Page configuration (safe if already set)
    try:
        st.set_page_config(
            page_title="HSBC Live+ | Control Center",
            page_icon="💳",
            layout="wide",
            initial_sidebar_state="collapsed",
        )
    except Exception:
        pass

    # Theme Configuration
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "Light"

    # ─── Multi-Card Router Gate ───────────────────────────────────────────────────
    if "selected_card" in st.session_state and "HDFC" in str(st.session_state["selected_card"]):
        hdfc_app_path = ROOT_DIR / "HDFC Diners Black Metal Statements" / "hdfc_dcbm_app.py"
        if hdfc_app_path.exists():
            import runpy
            runpy.run_path(str(hdfc_app_path), run_name="__main__")
            st.stop()

    is_light = st.session_state["theme_mode"] == "Light"

    # Theme Palettes
    if is_light:
        T = {
            "app_bg": "#fbf9f4",
            "text_main": "#18181b",
            "text_muted": "#71717a",
            "text_sub": "#8c8379",
            "border": "#e2ded5",
            "border_sub": "#ece8e1",
            "card_bg": "#ffffff",
            "card_border": "#e2ded5",
            "card_shadow": "0 4px 16px rgba(40, 30, 20, 0.05)",
            "hero_bg": "#ffffff",
            "hero_border": "#e2ded5",
            "subcard_bg": "#f5f3ed",
            "subcard_border": "#e2ded5",
            "accent_red": "#db0011",
            "accent_red_bg": "rgba(219, 0, 17, 0.08)",
            "accent_red_border": "rgba(219, 0, 17, 0.25)",
            "accent_green": "#15803d",
            "accent_green_bg": "rgba(21, 128, 61, 0.1)",
            "accent_green_border": "rgba(21, 128, 61, 0.25)",
            "accent_gold": "#9a6014",
            "accent_gold_bg": "rgba(154, 96, 20, 0.1)",
            "accent_gold_border": "rgba(154, 96, 20, 0.25)",
            "progress_bg": "#ede7dc",
            "sync_bg": "linear-gradient(135deg, #9a6014 0%, #784708 100%)",
            "sync_hover": "linear-gradient(135deg, #b47820 0%, #9a6014 100%)",
            "sync_border": "#b47820",
            "sync_shadow": "0 4px 14px rgba(154, 96, 20, 0.25)",
            "pill_time_bg": "rgba(154, 96, 20, 0.1)",
            "pill_time_color": "#9a6014",
            "pill_time_border": "rgba(154, 96, 20, 0.25)",
        }
    else:
        T = {
            "app_bg": "#0f172a",
            "text_main": "#f8fafc",
            "text_muted": "#94a3b8",
            "text_sub": "#64748b",
            "border": "#334155",
            "border_sub": "#1e293b",
            "card_bg": "#1e293b",
            "card_border": "#334155",
            "card_shadow": "0 4px 20px rgba(0, 0, 0, 0.35)",
            "hero_bg": "#1e293b",
            "hero_border": "#334155",
            "subcard_bg": "#0f172a",
            "subcard_border": "#334155",
            "accent_red": "#ef4444",
            "accent_red_bg": "rgba(239, 68, 68, 0.12)",
            "accent_red_border": "rgba(239, 68, 68, 0.3)",
            "accent_green": "#22c55e",
            "accent_green_bg": "rgba(34, 197, 94, 0.12)",
            "accent_green_border": "rgba(34, 197, 94, 0.3)",
            "accent_gold": "#fbbf24",
            "accent_gold_bg": "rgba(251, 191, 36, 0.12)",
            "accent_gold_border": "rgba(251, 191, 36, 0.3)",
            "progress_bg": "#334155",
            "sync_bg": "linear-gradient(135deg, #9a6014 0%, #784708 100%)",
            "sync_hover": "linear-gradient(135deg, #b47820 0%, #9a6014 100%)",
            "sync_border": "#b47820",
            "sync_shadow": "0 4px 14px rgba(154, 96, 20, 0.3)",
            "pill_time_bg": "rgba(59, 130, 246, 0.1)",
            "pill_time_color": "#60a5fa",
            "pill_time_border": "rgba(59, 130, 246, 0.25)",
        }

    # Inject Custom CSS matching V5 Prototype
    st.markdown(
        clean_html(f"""
        <style>
        .stApp {{
            background-color: {T["app_bg"]} !important;
            color: {T["text_main"]} !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
        }}
        [data-testid="stHeader"] {{
            background-color: transparent !important;
        }}
        [data-testid="stAppViewBlockContainer"] {{
            padding-top: 1.2rem !important;
            padding-bottom: 2rem !important;
            max-width: 1400px;
        }}

        /* Typography & Headings */
        h1, h2, h3, h4, h5, h6, p, span, div {{
            color: {T["text_main"]};
        }}

        /* Symmetrical Hero Card Container */
        .hsbc-card {{
            background: {T["card_bg"]};
            border: 1px solid {T["card_border"]};
            border-radius: 16px;
            padding: 22px;
            box-shadow: {T["card_shadow"]};
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 232px;
            margin-bottom: 16px;
            box-sizing: border-box;
        }}

        .hsbc-milestone-card {{
            background: {T["card_bg"]};
            border: 1px solid {T["card_border"]};
            border-radius: 16px;
            padding: 20px;
            box-shadow: {T["card_shadow"]};
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 185px;
            margin-bottom: 16px;
            box-sizing: border-box;
        }}

        /* Label Tag */
        .hsbc-label-tag {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}

        /* Card Headings */
        .hsbc-heading {{
            font-size: 16px;
            font-weight: 800;
            letter-spacing: -0.01em;
            color: {T["text_main"]};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* Big Metrics */
        .hsbc-metric-large {{
            font-size: 34px;
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.05;
        }}
        .hsbc-metric-unit {{
            font-size: 14px;
            font-weight: 600;
            color: {T["text_muted"]};
        }}
        .hsbc-metric-sub {{
            font-size: 12.5px;
            color: {T["text_muted"]};
            margin-top: 4px;
            font-weight: 500;
        }}

        /* Pills */
        .hsbc-pill {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 11.5px;
            font-weight: 700;
            letter-spacing: 0.02em;
            white-space: nowrap;
        }}
        .hsbc-pill-red {{
            background: {T["accent_red_bg"]};
            color: {T["accent_red"]};
            border: 1px solid {T["accent_red_border"]};
        }}
        .hsbc-pill-green {{
            background: {T["accent_green_bg"]};
            color: {T["accent_green"]};
            border: 1px solid {T["accent_green_border"]};
        }}
        .hsbc-pill-gold {{
            background: {T["accent_gold_bg"]};
            color: {T["accent_gold"]};
            border: 1px solid {T["accent_gold_border"]};
        }}
        .hsbc-pill-time {{
            background: {T["pill_time_bg"]};
            color: {T["pill_time_color"]};
            border: 1px solid {T["pill_time_border"]};
            font-size: 11.5px;
            font-weight: 700;
            padding: 0 10px;
            height: 36px;
            border-radius: 8px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            white-space: nowrap;
            box-sizing: border-box;
        }}

        /* Custom Progress Bars */
        .hsbc-progress-container {{
            width: 100%;
            height: 7px;
            background: {T["progress_bg"]};
            border-radius: 999px;
            overflow: hidden;
            margin: 6px 0;
        }}
        .hsbc-progress-bar {{
            height: 100%;
            border-radius: 999px;
            transition: width 0.3s ease;
        }}

        /* Subcards inside Headroom / Privileges */
        .hsbc-subcard {{
            background: {T["subcard_bg"]};
            border: 1px solid {T["subcard_border"]};
            border-radius: 10px;
            padding: 10px 12px;
            box-sizing: border-box;
        }}
        .hsbc-subcard-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 10px;
            background: {T["subcard_bg"]};
            border: 1px solid {T["subcard_border"]};
            border-radius: 8px;
            margin-bottom: 6px;
        }}

        /* Stat Badge Box */
        .hsbc-stat-badge {{
            background: {T["subcard_bg"]};
            border: 1px solid {T["subcard_border"]};
            border-radius: 8px;
            padding: 8px 12px;
            flex: 1 1 0;
        }}
        .hsbc-stat-label {{
            font-size: 10px;
            color: {T["text_muted"]};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .hsbc-stat-val {{
            font-size: 14.5px;
            font-weight: 800;
            color: {T["text_main"]};
            margin-top: 2px;
        }}

        /* Header Alignment & Controls */
        div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) {{
            align-items: center !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) div[data-testid="stButtonGroup"] button {{
            height: 36px !important;
            min-height: 36px !important;
            max-height: 36px !important;
            padding: 0 10px !important;
            font-size: 12.5px !important;
            line-height: 36px !important;
            font-weight: 600 !important;
            white-space: nowrap !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) div.stButton > button {{
            height: 36px !important;
            min-height: 36px !important;
            max-height: 36px !important;
            background: {T["sync_bg"]} !important;
            color: #ffffff !important;
            border: 1px solid {T["sync_border"]} !important;
            box-shadow: {T["sync_shadow"]} !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
            padding: 0 14px !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn) div.stButton > button:hover {{
            background: {T["sync_hover"]} !important;
        }}

        /* ─── Executive Theme Switcher & Segmented Control (Variant 2) ─── */
        div[data-testid="stButtonGroup"] {{
            background: {T["subcard_bg"]} !important;
            border: 1px solid {T["border"]} !important;
            border-radius: 10px !important;
            padding: 2px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        }}
        div[data-testid="stButtonGroup"] [data-baseweb="button-group"] {{
            gap: 2px !important;
        }}
        div[data-testid="stButtonGroup"] button,
        button[data-testid="stBaseButton-segmented_control"] {{
            border-radius: 8px !important;
            border: none !important;
            font-size: 12.5px !important;
            font-weight: 600 !important;
            padding: 0 12px !important;
            color: {T["text_muted"]} !important;
            background: transparent !important;
            transition: all 0.15s ease !important;
        }}
        div[data-testid="stButtonGroup"] button:hover,
        button[data-testid="stBaseButton-segmented_control"]:hover {{
            color: {T["text_main"]} !important;
            background: {'rgba(0,0,0,0.04)' if is_light else 'rgba(255,255,255,0.06)'} !important;
        }}
        /* Active Selection in Theme Switcher (High Contrast Solid Fill) */
        div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"],
        div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"],
        button[data-testid="stBaseButton-segmented_controlActive"] {{
            background: {'#1e293b' if is_light else '#f8fafc'} !important;
            color: {'#ffffff' if is_light else '#0f172a'} !important;
            font-weight: 700 !important;
            border: 1px solid {'#0f172a' if is_light else '#e2e8f0'} !important;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.14) !important;
        }}
        button[data-testid="stBaseButton-segmented_controlActive"] * {{
            color: {'#ffffff' if is_light else '#0f172a'} !important;
            font-weight: 700 !important;
        }}
        button[data-testid="stBaseButton-segmented_control"] * {{
            color: {T["text_muted"]} !important;
        }}

        /* ─── Selectbox for Card Switcher - Executive Variant 2 ─── */
        div[data-testid="stSelectbox"] {{
            margin-bottom: 0px !important;
        }}
        div[data-testid="stSelectbox"] div[data-baseweb="select"] {{
            background: {T["card_bg"]} !important;
            border: 1px solid {T["border"]} !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            font-size: 14.5px !important;
            color: {T["text_main"]} !important;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05) !important;
            height: 38px !important;
            min-height: 38px !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }}
        div[data-testid="stSelectbox"] div[data-baseweb="select"]:hover,
        div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {{
            border-color: {T["accent_red"]} !important;
            box-shadow: 0 2px 8px rgba(219, 0, 17, 0.15) !important;
        }}
        div[data-testid="stSelectbox"] div[data-baseweb="select"] * {{
            color: {T["text_main"]} !important;
            font-family: 'Outfit', sans-serif !important;
        }}
        div[data-baseweb="popover"] {{
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25) !important;
        }}
        div[data-baseweb="menu"] {{
            background: {T["card_bg"]} !important;
            border: 1px solid {T["border"]} !important;
            border-radius: 12px !important;
            padding: 6px !important;
        }}
        li[data-baseweb="menu-item"] {{
            border-radius: 8px !important;
            font-size: 13.5px !important;
            font-weight: 600 !important;
            color: {T["text_main"]} !important;
            padding: 8px 12px !important;
            margin-bottom: 2px !important;
        }}
        li[data-baseweb="menu-item"]:hover {{
            background-color: {T["subcard_bg"]} !important;
            color: {T["accent_red"]} !important;
        }}
        li[data-baseweb="menu-item"][aria-selected="true"] {{
            background-color: {'rgba(219, 0, 17, 0.12)' if is_light else 'rgba(219, 0, 17, 0.25)'} !important;
            color: {T["accent_red"]} !important;
            font-weight: 700 !important;
        }}

        /* Tabs styling */
        button[data-baseweb="tab"] {{
            font-weight: 700 !important;
            font-size: 14px !important;
            color: {T["text_muted"]} !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {T["accent_red"]} !important;
            border-bottom-color: {T["accent_red"]} !important;
        }}

        /* Section Titles */
        .hsbc-section-title {{
            font-size: 17px;
            font-weight: 800;
            color: {T["text_main"]};
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 10px;
            margin-bottom: 14px;
        }}

        /* Mobile Responsive Layout */
        @media (max-width: 768px) {{
            [data-testid="stAppViewBlockContainer"] {{
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
                padding-top: 0.8rem !important;
            }}
            /* Stack main columns */
            div[data-testid="stHorizontalBlock"]:has(.mobile-card-badge) {{
                display: flex !important;
                flex-direction: column !important;
                width: 100% !important;
                gap: 12px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(.mobile-card-badge) > div[data-testid="stColumn"] {{
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                flex: 1 1 100% !important;
            }}
            /* Controls row on mobile: Theme, Sync, Time side-by-side */
            div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn):not(:has(.mobile-card-badge)) {{
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                align-items: center !important;
                justify-content: space-between !important;
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
                flex: 0 0 auto !important;
                min-width: 110px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn):not(:has(.mobile-card-badge)) > div[data-testid="stColumn"]:nth-child(2) {{
                flex: 1 1 auto !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(.mobile-sync-btn):not(:has(.mobile-card-badge)) > div[data-testid="stColumn"]:last-child {{
                flex: 0 0 auto !important;
            }}
        }}
        </style>
        """),
        unsafe_allow_html=True,
    )

    # ─── Load Data ─────────────────────────────────────────────────────────────
    @st.cache_data(ttl=60)
    def load_data():
        alerts_file = CARD_DIR / "gmail_alerts.json"
        if not alerts_file.exists():
            try:
                hsbc_engine.trigger_live_sync(CARD_DIR)
            except Exception:
                pass
        return hsbc_engine.compute_hsbc_dashboard_data(CARD_DIR)

    data = load_data()

    # ─── Top Header Bar ────────────────────────────────────────────────────────
    col_head_left, col_head_right = st.columns([2.6, 1.4], vertical_alignment="center")

    with col_head_left:
        sub_c1, sub_c2 = st.columns([0.08, 0.92], vertical_alignment="center")
        with sub_c1:
            st.markdown(
                clean_html(f"""
                <div style="width: 38px; height: 38px; background: {T['accent_red']}; color: #ffffff; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 900; box-shadow: 0 3px 10px rgba(219, 0, 17, 0.3);">
                    H
                </div>
                """),
                unsafe_allow_html=True,
            )
        with sub_c2:
            card_col, badge_col = st.columns([1.5, 1.2], vertical_alignment="center")
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
                st.markdown(
                    clean_html(f"""
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="mobile-card-badge" style="font-size: 13.5px; font-weight: 700; color: {T['text_main']}; background: {T['subcard_bg']}; padding: 3px 10px; border-radius: 8px; border: 1px solid {T['border']};">
                            •••• {data['card_ending']}
                        </span>
                        <span class="hsbc-pill hsbc-pill-gold" style="font-size: 11px;">
                            Visa Infinite
                        </span>
                    </div>
                    """),
                    unsafe_allow_html=True,
                )
            st.markdown(
                clean_html(f"""
                <div class="mobile-header-sub" style="font-size: 13px; color: {T['text_sub']}; font-weight: 500; margin-top: 2px;">
                    Automated Real-Time Cashback & Spend Tracker from Gmail InstaAlerts
                </div>
                """),
                unsafe_allow_html=True,
            )

    with col_head_right:
        btn_col1, btn_col2, btn_col3 = st.columns([1.25, 1.05, 0.9], vertical_alignment="center")
        with btn_col1:
            selected_theme = st.segmented_control(
                "Theme",
                options=["Light", "Dark"],
                default=st.session_state["theme_mode"],
                label_visibility="collapsed",
            )
            if selected_theme and selected_theme != st.session_state["theme_mode"]:
                st.session_state["theme_mode"] = selected_theme
                st.rerun()
        with btn_col2:
            st.markdown("<div class='mobile-sync-btn' style='display:none;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Sync", use_container_width=True):
                with st.spinner("Fetching latest alerts from Gmail..."):
                    try:
                        sync_res = hsbc_engine.trigger_live_sync(CARD_DIR)
                        st.cache_data.clear()
                        st.toast(f"✅ Synced {sync_res.get('alert_count', 0)} alerts!", icon="📬")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Sync error: {exc}")
        with btn_col3:
            sync_time_str = data["sync_metadata"]["last_synced"]
            try:
                dt = datetime.datetime.fromisoformat(sync_time_str)
                friendly_time = dt.strftime("%d %b %H:%M")
            except Exception:
                friendly_time = "Live"
            st.markdown(
                clean_html(f"""
                <div style="text-align: right;">
                    <span class="hsbc-pill-time">
                        ● {friendly_time}
                    </span>
                </div>
                """),
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # ─── Section 1: Hero Cashback & Headroom (3 Equal Symmetrical Columns) ──────
    h_col1, h_col2, h_col3 = st.columns(3)

    cycle_info = data["cycle"]
    cap_info = data["cashback_cap"]
    portfolio = data["portfolio"]

    # Tile 1: 10% Cashback Tracker
    with h_col1:
        st.markdown(
            clean_html(f"""
            <div class="hsbc-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: {T['accent_red']};">10% Cashback</div>
                            <div class="hsbc-heading">{cycle_info['label']}</div>
                        </div>
                        <span class="hsbc-pill hsbc-pill-red">⏳ {cycle_info['reset_str']}</span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 6px;">
                        <span class="hsbc-metric-large" style="color: {T['text_main']};">₹{cap_info['earned']:.2f}</span>
                        <span class="hsbc-metric-unit">/ ₹{cap_info['cap_limit']:,.0f} Cashback</span>
                    </div>
                    <div class="hsbc-metric-sub">₹{cap_info['remaining_cb']:,.2f} remaining this cycle</div>
                </div>

                <div style="margin-top: 16px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: {T['text_muted']}; font-weight: 600;">
                        <span>Cap Used: <b>{cap_info['percent_used']}%</b></span>
                        <span>Accelerated Spend: <b>₹{cap_info['accelerated_spend']:,.0f} / ₹{cap_info['max_accelerated_spend']:,.0f}</b></span>
                    </div>
                    <div class="hsbc-progress-container">
                        <div class="hsbc-progress-bar" style="width: {min(100.0, cap_info['percent_used'])}%; background: {T['accent_red']};"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: {T['text_muted']};">
                        <span>Cycle: <b>{datetime.date.fromisoformat(cycle_info['start']).strftime('%d %b')} – {datetime.date.fromisoformat(cycle_info['end']).strftime('%d %b')}</b></span>
                        <span>Monthly Limit: <b>₹{cap_info['cap_limit']:,.0f}</b></span>
                    </div>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    # Tile 2: Food Delivery, Groceries, Dining - Remaining Room
    with h_col2:
        st.markdown(
            clean_html(f"""
            <div class="hsbc-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: {T['text_muted']};">Remaining Room</div>
                            <div class="hsbc-heading">Food Delivery, Groceries, Dining</div>
                        </div>
                        <span class="hsbc-pill hsbc-pill-green">10% Rate</span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 6px; margin-top: 6px;">
                        <span class="hsbc-metric-large" style="color: {T['accent_red']};">₹{cap_info['remaining_accelerated_spend']:,.0f}</span>
                        <span class="hsbc-metric-unit">spend left</span>
                    </div>
                    <div class="hsbc-metric-sub">Spend headroom before reaching ₹{cap_info['cap_limit']:,.0f} cap</div>
                </div>

                <div style="margin-top: 16px;">
                    <div class="hsbc-subcard">
                        <div style="font-size: 10.5px; font-weight: 700; color: {T['text_muted']}; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 3px;">
                            Eligible Merchants & Platforms
                        </div>
                        <div style="font-size: 12px; color: {T['text_sub']}; line-height: 1.4;">
                            Zomato, Swiggy, Blinkit, Zepto, BigBasket, Instamart, Nature's Basket, standalone restaurants & cafes
                        </div>
                    </div>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    # Tile 3: Direct Statement Savings & Portfolio
    with h_col3:
        st.markdown(
            clean_html(f"""
            <div class="hsbc-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: {T['text_muted']};">Direct Statement Savings</div>
                            <div class="hsbc-heading">Portfolio Net Savings</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 6px; margin-top: 6px;">
                        <span class="hsbc-metric-large" style="color: {T['accent_green']};">₹{portfolio['lifetime_cashback']:,.2f}</span>
                        <span class="hsbc-metric-unit">lifetime</span>
                    </div>
                    <div class="hsbc-metric-sub">Credited directly to reduce statement balance</div>
                </div>

                <div style="margin-top: 16px;">
                    <div style="display: flex; gap: 8px;">
                        <div class="hsbc-stat-badge">
                            <div class="hsbc-stat-label">TOTAL SPEND TRACKED</div>
                            <div class="hsbc-stat-val">₹{portfolio['lifetime_spend']:,.2f}</div>
                        </div>
                        <div class="hsbc-stat-badge">
                            <div class="hsbc-stat-label">EFFECTIVE REWARD RATE</div>
                            <div class="hsbc-stat-val">{portfolio['effective_reward_rate']:.2f}%</div>
                        </div>
                    </div>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    # ─── Section 2: Milestones, Fee Waiver & Lounge Perks ───────────────────────
    st.markdown(
        clean_html(f"<div class='hsbc-section-title'>🎯 Milestones, Fee Waiver & Travel Privileges</div>"),
        unsafe_allow_html=True,
    )

    m_col1, m_col2, m_col3 = st.columns(3)

    welcome = data["welcome"]
    fee = data["fee_waiver"]
    lounge = data["lounge"]

    # Milestone 1: Welcome Offer
    with m_col1:
        st.markdown(
            clean_html(f"""
            <div class="hsbc-milestone-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: {T['text_muted']};">30-Day Welcome Benefit</div>
                            <div class="hsbc-heading">₹{welcome['reward']:,} Welcome Cashback</div>
                        </div>
                        <span class="hsbc-pill hsbc-pill-green">✔ Unlocked</span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 6px; margin-top: 4px;">
                        <span style="font-size: 24px; font-weight: 800; color: {T['accent_green']};">₹{welcome['spent']:,.0f}</span>
                        <span style="font-size: 13.5px; color: {T['text_muted']}; font-weight: 600;">/ ₹{welcome['target']:,.0f} spent</span>
                    </div>
                </div>
                <div style="margin-top: 12px;">
                    <div class="hsbc-progress-container">
                        <div class="hsbc-progress-bar" style="width: 100%; background: {T['accent_green']};"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 11.5px; color: {T['text_muted']};">
                        <span>Target Met in First 30 Days</span>
                        <span>+ ₹750 Activation Voucher</span>
                    </div>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    # Milestone 2: Annual Fee Waiver
    with m_col2:
        st.markdown(
            clean_html(f"""
            <div class="hsbc-milestone-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: {T['text_muted']};">Annual Fee Waiver</div>
                            <div class="hsbc-heading">Save ₹{fee['annual_fee']} + GST</div>
                        </div>
                        <span class="hsbc-pill hsbc-pill-gold">⏳ {fee['days_left']}D Left</span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 6px; margin-top: 4px;">
                        <span style="font-size: 24px; font-weight: 800; color: {T['text_main']};">₹{fee['spent']:,.0f}</span>
                        <span style="font-size: 13.5px; color: {T['text_muted']}; font-weight: 600;">/ ₹{fee['target']:,.0f} ({fee['percent']}%)</span>
                    </div>
                </div>
                <div style="margin-top: 12px;">
                    <div class="hsbc-progress-container">
                        <div class="hsbc-progress-bar" style="width: {min(100.0, fee['percent'])}%; background: {T['accent_gold']};"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 11.5px; color: {T['text_muted']};">
                        <span>Remaining: <b>₹{fee['remaining']:,.0f}</b></span>
                        <span>Run-rate: <b>₹{fee['run_rate_needed']:,.0f} / day</b></span>
                    </div>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    # Milestone 3: Lounge & Travel Perks
    with m_col3:
        st.markdown(
            clean_html(f"""
            <div class="hsbc-milestone-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                        <div>
                            <div class="hsbc-label-tag" style="color: {T['text_muted']};">Visa Infinite Privileges</div>
                            <div class="hsbc-heading">Lounge & Global eSIM</div>
                        </div>
                        <span class="hsbc-pill hsbc-pill-green">Available</span>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 5px; margin-top: 6px;">
                        <div class="hsbc-subcard-row">
                            <span style="font-size: 12px; font-weight: 600;">Domestic Lounge (Jul–Dec)</span>
                            <span class="hsbc-pill hsbc-pill-green" style="font-size: 10px; padding: 2px 7px;">{lounge['domestic_h2']}</span>
                        </div>
                        <div class="hsbc-subcard-row">
                            <span style="font-size: 12px; font-weight: 600;">International Lounge (Annual)</span>
                            <span class="hsbc-pill hsbc-pill-green" style="font-size: 10px; padding: 2px 7px;">{lounge['international']}</span>
                        </div>
                        <div class="hsbc-subcard-row" style="margin-bottom: 0;">
                            <span style="font-size: 12px; font-weight: 600;">Complimentary 1GB Global eSIM</span>
                            <span class="hsbc-pill hsbc-pill-green" style="font-size: 10px; padding: 2px 7px;">{lounge['esim']}</span>
                        </div>
                    </div>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    # ─── Section 3: Tabs Section ───────────────────────────────────────────────
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    tab_txns, tab_history, tab_perks = st.tabs([
        "📋 Live Transactions (Current Cycle)",
        "📊 Monthly History & Caps",
        "🍷 Live+ Reserve & Dining Perks",
    ])

    # Tab 1: Live Transactions
    with tab_txns:
        cycle_txns = data["transactions"]["current_cycle"]
        all_txns = data["transactions"]["all"]

        t_head_c1, t_head_c2 = st.columns([3, 1], vertical_alignment="center")
        with t_head_c1:
            st.markdown(
                clean_html(f"<div style='font-weight: 700; font-size: 15px;'>Statement Cycle: {datetime.date.fromisoformat(cycle_info['start']).strftime('%d %b %Y')} – {datetime.date.fromisoformat(cycle_info['end']).strftime('%d %b %Y')}</div>"),
                unsafe_allow_html=True,
            )
        with t_head_c2:
            st.markdown(
                clean_html(f"<div style='text-align: right;'><span class='hsbc-pill hsbc-pill-green'>{len(cycle_txns)} Transactions Audited</span></div>"),
                unsafe_allow_html=True,
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
        with st.expander("🔍 View All Historical Transactions Across Cycles", expanded=False):
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
        st.markdown(
            clean_html("<div style='font-weight: 700; font-size: 15px; margin-bottom: 12px;'>Historical Cashback by Cycle</div>"),
            unsafe_allow_html=True,
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
        st.markdown(
            clean_html("<div style='font-weight: 700; font-size: 15px; margin-bottom: 14px;'>Curated Visa Infinite & Live+ Reserve Benefits</div>"),
            unsafe_allow_html=True,
        )
        p_c1, p_c2, p_c3 = st.columns(3)
        with p_c1:
            st.markdown(
                clean_html(f"""
                <div class="hsbc-subcard" style="padding: 16px;">
                    <div style="font-weight: 800; font-size: 14.5px; color: {T['text_main']};">🍽️ The Live+ Reserve (TimesPrime)</div>
                    <div style="font-size: 12.5px; color: {T['text_muted']}; margin-top: 6px; line-height: 1.4;">
                        Curated menus & complimentary dessert/drinks at Indian Accent, Tresind, Comorin, Olive.
                    </div>
                </div>
                """),
                unsafe_allow_html=True,
            )
        with p_c2:
            st.markdown(
                clean_html(f"""
                <div class="hsbc-subcard" style="padding: 16px;">
                    <div style="font-weight: 800; font-size: 14.5px; color: {T['text_main']};">🎟️ BOGO Cinema Tickets</div>
                    <div style="font-size: 12.5px; color: {T['text_muted']}; margin-top: 6px; line-height: 1.4;">
                        Buy-1-Get-1 free movie tickets via District by Zomato and BookMyShow.
                    </div>
                </div>
                """),
                unsafe_allow_html=True,
            )
        with p_c3:
            st.markdown(
                clean_html(f"""
                <div class="hsbc-subcard" style="padding: 16px;">
                    <div style="font-weight: 800; font-size: 14.5px; color: {T['text_main']};">🏨 ITC Hotels Stay 2 Pay 1</div>
                    <div style="font-size: 12.5px; color: {T['text_muted']}; margin-top: 6px; line-height: 1.4;">
                        Complimentary 3rd night on 2 paid nights, or 50% off 2nd night at luxury ITC properties.
                    </div>
                </div>
                """),
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    render_app()
