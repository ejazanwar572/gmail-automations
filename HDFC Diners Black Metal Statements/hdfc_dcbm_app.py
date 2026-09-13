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
        page_title="HDFC Diners Black Metal | Control Center",
        page_icon="💳",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
except Exception:
    pass

# ─── Theme Configuration (Dark / Haute Metal Light) ──────────────────────────
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "Light"

# Optional Cloud Authentication gate (set DASHBOARD_PASSWORD in Streamlit secrets for cloud deploy)
cloud_password = None
try:
    if hasattr(st, "secrets") and "DASHBOARD_PASSWORD" in st.secrets:
        cloud_password = st.secrets["DASHBOARD_PASSWORD"]
except Exception:
    cloud_password = None

if cloud_password:
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        _, auth_col, _ = st.columns([1, 1.2, 1])
        with auth_col:
            st.markdown("<div style='text-align: center; margin-top: 100px;'><span style='font-size: 48px;'>💳</span><h2>HDFC DCBM Control Center</h2><p style='color: #8c8379;'>Enter PIN to unlock your personal rewards dashboard</p></div>", unsafe_allow_html=True)
            entered_pin = st.text_input("Access PIN", type="password", key="cloud_pin_input")
            if entered_pin:
                if entered_pin == str(cloud_password):
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Incorrect PIN.")
        st.stop()

# ─── Multi-Card Router Gate ───────────────────────────────────────────────────
if "selected_card" in st.session_state and "HSBC" in str(st.session_state["selected_card"]):
    hsbc_app_path = ROOT_DIR / "HSBC Live Plus Statements" / "hsbc_live_plus_app.py"
    if hsbc_app_path.exists():
        import runpy
        runpy.run_path(str(hsbc_app_path), run_name="__main__")
        st.stop()

is_light = st.session_state["theme_mode"] == "Light"

# Theme Palettes: Metallic Dark vs Haute Metal (Bespoke Champagne & Onyx)
if is_light:
    T = {
        "app_bg": "#f7f4ee",
        "text_main": "#1a1613",
        "text_muted": "#6e675f",
        "text_sub": "#8c8379",
        "border": "#dfd5c6",
        "border_sub": "#efeae0",
        "card_bg": "#ffffff",
        "card_border": "#dfd5c6",
        "card_shadow": "0 4px 16px rgba(60, 50, 40, 0.05)",
        "hero_bg": "#ffffff",
        "hero_border": "#d8cbba",
        "hero_shadow": "0 10px 28px rgba(154, 96, 20, 0.08), 0 2px 6px rgba(0, 0, 0, 0.03)",
        "subcard_bg": "#faf8f4",
        "subcard_border": "#dfd5c6",
        "input_bg": "#faf8f4",
        "input_border": "#cec2b0",
        "input_text": "#1a1613",
        "input_focus_border": "#9a6014",
        "input_focus_shadow": "rgba(154, 96, 20, 0.2)",
        "btn_bg": "linear-gradient(135deg, #9a6014 0%, #784708 100%)",
        "btn_hover": "linear-gradient(135deg, #b47820 0%, #9a6014 100%)",
        "btn_border": "#b47820",
        "btn_shadow": "0 4px 14px rgba(154, 96, 20, 0.25)",
        "progress_bg": "#ede7dc",
        "progress_fill": "linear-gradient(90deg, #9a6014 0%, #c48e38 100%)",
        "chip_bg": "#ffffff",
        "chip_border": "#dfd5c6",
        "card_number_badge_bg": "#ede7dc",
        "card_number_badge_border": "#cec2b0",
        "card_number_badge_color": "#38322b",
        "footer_border": "#dfd5c6",
        "footer_text": "#8c8379",
        "val_hl_bg": "#faf7f2",
        "val_hl_border": "#cec2b0",
        "accent_gold": "#9a6014",
        "accent_green": "#15803d",
        "accent_amber": "#b45309",
    }
else:
    T = {
        "app_bg": "#0b0f19",
        "text_main": "#f1f5f9",
        "text_muted": "#94a3b8",
        "text_sub": "#64748b",
        "border": "#1e293b",
        "border_sub": "#334155",
        "card_bg": "linear-gradient(145deg, #131b2e 0%, #0d1322 100%)",
        "card_border": "#1e293b",
        "card_shadow": "0 4px 20px -2px rgba(0, 0, 0, 0.4)",
        "hero_bg": "linear-gradient(135deg, #101c38 0%, #0b1224 100%)",
        "hero_border": "#2563eb",
        "hero_shadow": "0 8px 30px rgba(37, 99, 235, 0.15)",
        "subcard_bg": "#0f172a",
        "subcard_border": "#1e293b",
        "input_bg": "#1a233a",
        "input_border": "#334155",
        "input_text": "#ffffff",
        "input_focus_border": "#3b82f6",
        "input_focus_shadow": "rgba(59, 130, 246, 0.25)",
        "btn_bg": "linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)",
        "btn_hover": "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
        "btn_border": "#3b82f6",
        "btn_shadow": "0 4px 14px rgba(37, 99, 235, 0.25)",
        "progress_bg": "#1e293b",
        "progress_fill": "linear-gradient(90deg, #3b82f6 0%, #10b981 100%)",
        "chip_bg": "#101a2f",
        "chip_border": "#1e293b",
        "card_number_badge_bg": "#1e293b",
        "card_number_badge_border": "#334155",
        "card_number_badge_color": "#94a3b8",
        "footer_border": "#1e293b",
        "footer_text": "#475569",
        "val_hl_bg": "linear-gradient(145deg, #132238 0%, #0d1627 100%)",
        "val_hl_border": "#3b82f6",
        "accent_gold": "#d97706",
        "accent_green": "#22c55e",
        "accent_amber": "#f59e0b",
    }

st.html(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    html, body, [class*="css"], .stMarkdown, p, div, label, span, h1, h2, h3, h4, h5, h6 {{
        font-family: 'Outfit', sans-serif !important;
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
        background-color: {T["app_bg"]} !important;
        color: {T["text_main"]} !important;
    }}

    /* Top header space removal */
    [data-testid="stToolbar"], #stDecoration {{ display: none !important; }}
    header[data-testid="stHeader"] {{
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        background-color: {T["app_bg"]} !important;
    }}
    [data-testid="stAppViewBlockContainer"] {{
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }}

    /* Card container */
    .metal-card {{
        background: {T["card_bg"]};
        border: 1px solid {T["card_border"]};
        border-radius: 16px;
        padding: 24px;
        box-shadow: {T["card_shadow"]};
        margin-bottom: 20px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    .metal-card:hover {{
        border-color: {T["border_sub"]};
    }}

    /* Hero Card */
    .hero-card {{
        background: {T["hero_bg"]};
        border: 1px solid {T["hero_border"]};
        border-radius: 18px;
        padding: 26px;
        box-shadow: {T["hero_shadow"]};
        margin-bottom: 24px;
    }}

    /* Badge Pills */
    .pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }}
    .pill-green {{
        background: rgba(21, 128, 61, 0.12);
        color: {'#15803d' if is_light else '#34d399'};
        border: 1px solid rgba(21, 128, 61, 0.3);
    }}
    .pill-orange {{
        background: rgba(180, 83, 9, 0.12);
        color: {'#b45309' if is_light else '#fbbf24'};
        border: 1px solid rgba(180, 83, 9, 0.3);
    }}
    .pill-red {{
        background: rgba(220, 38, 38, 0.12);
        color: {'#dc2626' if is_light else '#f87171'};
        border: 1px solid rgba(220, 38, 38, 0.3);
    }}
    .pill-blue {{
        background: rgba(154, 96, 20, 0.1);
        color: {'#9a6014' if is_light else '#60a5fa'};
        border: 1px solid rgba(154, 96, 20, 0.28);
    }}

    /* Big metric numbers */
    .hero-number {{
        font-size: 42px;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.05;
        color: {T["text_main"]};
    }}
    .hero-sub {{
        font-size: 14px;
        color: {T["text_muted"]};
        font-weight: 500;
        margin-top: 4px;
    }}

    /* Buttons & Download Buttons */
    div.stButton > button, div[data-testid="stDownloadButton"] > button {{
        background: {T["btn_bg"]} !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        border: 1px solid {T["btn_border"]} !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 9px 18px !important;
        box-shadow: {T["btn_shadow"]} !important;
        transition: all 0.2s ease !important;
    }}
    div.stButton > button:hover, div[data-testid="stDownloadButton"] > button:hover {{
        background: {T["btn_hover"]} !important;
        border-color: {'#d97706' if is_light else '#818cf8'} !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
    }}

    /* Input controls: Selectboxes, Text Inputs, Multiselects */
    .stTextInput input, .stNumberInput input {{
        background-color: {T["input_bg"]} !important;
        color: {T["input_text"]} !important;
        border: 1px solid {T["input_border"]} !important;
        border-radius: 10px !important;
        font-size: 14px !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus {{
        border-color: {T["input_focus_border"]} !important;
        box-shadow: 0 0 0 2px {T["input_focus_shadow"]} !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: {T["input_bg"]} !important;
        color: {T["input_text"]} !important;
        border: 1px solid {T["input_border"]} !important;
        border-radius: 10px !important;
        font-size: 14px !important;
    }}
    div[data-baseweb="select"] span {{
        color: {T["input_text"]} !important;
    }}
    span[data-baseweb="tag"] {{
        background-color: {'#9a6014' if is_light else '#2563eb'} !important;
        border: 1px solid {'#b47820' if is_light else '#3b82f6'} !important;
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
        font-size: 15px !important;
        color: {T["text_main"]} !important;
    }}
    [data-testid="stExpander"] {{
        border: 1px solid {T["border"]} !important;
        border-radius: 12px !important;
        background: {T["card_bg"]} !important;
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
        font-weight: 700 !important;
        font-size: 14px !important;
        color: {T["text_muted"]} !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {'#9a6014' if is_light else '#60a5fa'} !important;
        border-bottom-color: {'#9a6014' if is_light else '#60a5fa'} !important;
    }}

    /* Streamlit Dataframe */
    div[data-testid="stDataFrame"] {{
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid {T["border"]} !important;
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
        background: {'#ffffff' if is_light else '#131b2e'} !important;
        background-color: {'#ffffff' if is_light else '#131b2e'} !important;
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
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        background: {'#ffffff' if is_light else '#131b2e'} !important;
        background-color: {'#ffffff' if is_light else '#131b2e'} !important;
        border: none !important;
        border-radius: 10px !important;
        height: 36px !important;
        min-height: 36px !important;
    }}
    div[data-testid="stSelectbox"] div[data-baseweb="select"]:hover,
    div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within {{
        border-color: {T["accent_gold"]} !important;
        box-shadow: 0 2px 8px rgba(154, 96, 20, 0.15) !important;
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
        color: {T["accent_gold"]} !important;
    }}
    li[data-baseweb="menu-item"][aria-selected="true"] {{
        background-color: {'rgba(154, 96, 20, 0.12)' if is_light else 'rgba(154, 96, 20, 0.25)'} !important;
        color: {T["accent_gold"]} !important;
        font-weight: 700 !important;
    }}

    /* ─── Mobile Responsive Enhancements ─── */
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

        /* Make tab list scrollable smoothly on narrow screens */
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

        /* Buttons & controls mobile touch friendliness */
        div.stButton > button, div[data-testid="stDownloadButton"] > button {{
            padding: 7px 14px !important;
            font-size: 13px !important;
        }}

        /* Mobile header: stack title on top, controls in a clean row below */
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

        /* Keep the 3 header controls (Theme, Sync, Timestamp) nicely side-by-side in their inner row on mobile */
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
col_head_left, col_head_right = st.columns([2.6, 1.4], vertical_alignment="center")

with col_head_left:
    sub_c1, sub_c2 = st.columns([0.08, 0.92], vertical_alignment="center")
    with sub_c1:
        st.markdown(
            f"""
            <div style="width: 38px; height: 38px; background: {'#faf8f4' if is_light else '#1e293b'}; color: {T['accent_gold']}; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 900; border: 1px solid {T['border']};">
                💳
            </div>
            """,
            unsafe_allow_html=True,
        )
    with sub_c2:
        card_col, badge_col = st.columns([1.5, 1.2], vertical_alignment="center")
        with card_col:
            st.markdown(
                f"""
                <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: {'#9a6014' if is_light else '#fbbf24'}; margin-bottom: 2px;">
                    Selected Card Account
                </div>
                """,
                unsafe_allow_html=True,
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
            st.markdown(
                f"""
                <div style="margin-top: 15px; display: flex; align-items: center; gap: 8px;">
                    <span class="mobile-card-badge" style="font-size: 13px; font-weight: 700; color: {T['card_number_badge_color']}; background: {T['card_number_badge_bg']}; padding: 3px 10px; border-radius: 8px; border: 1px solid {T['card_number_badge_border']};">
                        •••• 2360
                    </span>
                    <span class="pill pill-blue" style="font-size: 11px;">
                        Diners Club Metal
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown(
            f"""
            <div class="mobile-header-sub" style="font-size: 13px; color: {T['text_sub']}; font-weight: 500; margin-top: 2px;">
                Automated Real-Time Rewards & Spend Tracker from Gmail InstaAlerts
            </div>
            """,
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
                    sync_res = dcbm_engine.trigger_live_sync(CARD_DIR)
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
            f"""
            <div style="text-align: right;">
                <span class="pill pill-blue" style="font-size: 11px; white-space: nowrap; padding: 4px 8px;">
                    ● {friendly_time}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ─── SECTION 1: HERO CAP MONITOR ──────────────────────────────────────────────
st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

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

# Render Hero Cards
hero_col1, hero_col2, hero_col3 = st.columns([1.35, 1.25, 1.4])

with hero_col1:
    today_earned = active_cap.get("today_earned", 0)
    today_daily_cap = active_cap.get("daily_cap", 2500)
    today_percent = min(100.0, round((today_earned / today_daily_cap) * 100, 1)) if today_daily_cap > 0 else 0.0

    st.markdown(
        f"""
        <div class="hero-card" style="height: 240px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                    <div>
                        <div style="font-size: 13px; font-weight: 700; color: {'#9a6014' if is_light else '#60a5fa'}; text-transform: uppercase; letter-spacing: 0.05em;">
                            Accelerated Reward Points Limit
                        </div>
                        <div style="font-size: 18px; font-weight: 700; color: {T['text_main']};">
                            {cycle_title}
                        </div>
                    </div>
                    <span class="pill pill-blue" style="font-size: 11px; padding: 4px 10px; white-space: nowrap;">
                        ⏳ {'Resets Today' if active_cap['days_remaining'] == 0 else ('Resets Tomorrow' if active_cap['days_remaining'] == 1 else f"Resets in {active_cap['days_remaining']} days")}
                    </span>
                </div>
                <div style="display: flex; align-items: baseline; gap: 8px;">
                    <span class="hero-number">{active_cap["remaining"]:,}</span>
                    <span style="font-size: 18px; font-weight: 600; color: {T['text_muted']};">/ {active_cap["monthly_cap"]:,} RP remaining</span>
                </div>
                <div class="hero-sub">{active_cap["percent_remaining"]}% of monthly cap still available to earn</div>
            </div>
            <div style="margin-top: 10px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: {T['text_muted']}; margin-bottom: 4px;">
                    <span>Monthly Progress: <b>{active_cap["earned"]:,} / {active_cap["monthly_cap"]:,} RP</b></span>
                    <span>Today: <b>{today_earned:,} / {today_daily_cap:,} RP</b></span>
                </div>
                <div style="background: {T['progress_bg']}; border-radius: 999px; height: 10px; overflow: hidden; margin-bottom: 4px;">
                    <div style="background: {T['progress_fill']}; width: {min(100.0, active_cap['percent_used'])}%; height: 100%;"></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with hero_col2:
    st.markdown(
        f"""
        <div class="metal-card" style="height: 240px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="font-size: 13px; font-weight: 700; color: {T['text_muted']}; text-transform: uppercase; letter-spacing: 0.05em;">
                    Remaining Spend Headroom
                </div>
                <div style="font-size: 14px; color: {T['text_sub']}; margin-top: 2px;">
                    Spend buffer before hitting 10,000 RP cap
                </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 10px;">
                <div style="background: {T['subcard_bg']}; padding: 10px 14px; border-radius: 12px; border: 1px solid {T['subcard_border']}; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 12px; color: {T['text_muted']}; font-weight: 600;">✈️ SmartBuy Flights (5X)</div>
                        <div style="font-size: 20px; font-weight: 800; color: {'#9a6014' if is_light else '#38bdf8'};">₹{active_cap["flight_spend_capacity"]:,}</div>
                    </div>
                    <span style="font-size: 12px; color: {T['text_sub']}; text-align: right;">4X bonus<br>(20 RP / ₹150)</span>
                </div>
                <div style="background: {T['subcard_bg']}; padding: 10px 14px; border-radius: 12px; border: 1px solid {T['subcard_border']}; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 12px; color: {T['text_muted']}; font-weight: 600;">🏨 SmartBuy Hotels (10X)</div>
                        <div style="font-size: 20px; font-weight: 800; color: {'#784708' if is_light else '#a78bfa'};">₹{active_cap["hotel_spend_capacity"]:,}</div>
                    </div>
                    <span style="font-size: 12px; color: {T['text_sub']}; text-align: right;">9X bonus<br>(45 RP / ₹150)</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with hero_col3:
    st.markdown(
        f"""
        <div class="metal-card" style="height: 240px; padding: 24px; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 13px; font-weight: 700; color: {T['text_muted']}; text-transform: uppercase; letter-spacing: 0.05em;">
                        Reward Points Details
                    </div>
                    <span class="pill pill-green" style="font-size: 10px; padding: 2px 7px;">
                        1 RP = ₹1.00
                    </span>
                </div>
                <div style="font-size: 13px; color: {T['text_sub']}; margin-top: 2px;">
                    Net Balance & Portfolio Value
                </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
                <div style="background: {T['subcard_bg']}; padding: 5px 12px; border-radius: 10px; border: 1px solid {T['subcard_border']}; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 11px; color: {T['text_muted']}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em;">Lifetime Reward Points</div>
                        <div style="font-size: 10.5px; color: {T['text_sub']}; line-height: 1.1;">Total points earned to date</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 17px; font-weight: 800; color: {'#b45309' if is_light else '#fbbf24'}; letter-spacing: -0.01em;">{lifetime_earned:,}</span>
                        <span style="font-size: 11px; font-weight: 600; color: {T['text_muted']};"> RP</span>
                    </div>
                </div>
                <div style="background: {T['subcard_bg']}; padding: 5px 12px; border-radius: 10px; border: 1px solid {T['subcard_border']}; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 11px; color: {T['text_muted']}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em;">Current Available</div>
                        <div style="font-size: 10.5px; color: {T['text_sub']}; line-height: 1.1;">Worth <b>₹{current_available:,}</b> on SmartBuy</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 17px; font-weight: 800; color: {'#9a6014' if is_light else '#38bdf8'}; letter-spacing: -0.01em;">{current_available:,}</span>
                        <span style="font-size: 11px; font-weight: 600; color: {T['text_muted']};"> RP</span>
                    </div>
                </div>
                <div style="background: {T['subcard_bg']}; padding: 5px 12px; border-radius: 10px; border: 1px solid {T['subcard_border']}; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 11px; color: {T['text_muted']}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em;">My Reward Rate</div>
                        <div style="font-size: 10.5px; color: {T['text_sub']}; line-height: 1.1;">{lifetime_earned:,} RP / ₹{total_spend_all:,.0f} spend</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 17px; font-weight: 800; color: {'#15803d' if is_light else '#34d399'}; letter-spacing: -0.01em;">{lifetime_reward_rate:.2f}%</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─── SECTION 2: MILESTONES ROW ────────────────────────────────────────────────
st.markdown(f"<div style='font-size: 18px; font-weight: 700; margin: 10px 0 14px 0; color: {T['text_main']};'>🎯 Spend Milestones & Fee Waiver</div>", unsafe_allow_html=True)

m_col1, m_col2, m_col3 = st.columns(3)

# 1. Welcome Milestone
welcome = data["milestones"]["welcome"]
with m_col1:
    status_tag = "✅ UNLOCKED" if welcome["met"] else f"⏳ {welcome['days_left']}d left"
    tag_class = "pill-green" if welcome["met"] else "pill-blue"
    st.markdown(
        f"""
        <div class="metal-card" style="min-height: 236px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <div style="font-size: 12px; font-weight: 700; color: {T['text_muted']}; text-transform: uppercase;">Welcome Milestone</div>
                        <div style="font-size: 16px; font-weight: 700; color: {T['text_main']};">₹1.5 Lakhs in 90 Days</div>
                    </div>
                    <span class="pill {tag_class}">{status_tag}</span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: {'#15803d' if is_light else '#10b981'}; margin: 6px 0;">
                    ₹{welcome["spend"]:,.0f} <span style="font-size: 14px; font-weight: 500; color: {T['text_sub']};">/ ₹{welcome["target"]:,.0f}</span>
                    <span style="font-size: 13px; font-weight: 700; color: {'#15803d' if is_light else '#34d399'}; margin-left: 6px;">({welcome['progress']}%)</span>
                </div>
                <div style="background: {T['progress_bg']}; border-radius: 999px; height: 8px; margin: 8px 0; overflow: hidden;">
                    <div style="background: {'#15803d' if is_light else '#10b981'}; width: {welcome['progress']}%; height: 100%;"></div>
                </div>
            </div>
            <div style="background: {T['subcard_bg']}; border: 1px solid {T['subcard_border']}; border-radius: 10px; padding: 9px 12px; display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                <div>
                    <div style="font-size: 10px; font-weight: 700; color: {T['text_sub']}; text-transform: uppercase; letter-spacing: 0.05em;">Perks Status</div>
                    <div style="font-size: 13px; font-weight: 800; color: {'#15803d' if is_light else '#34d399'};">Unlocked & Claimed</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 10px; font-weight: 700; color: {T['text_sub']}; text-transform: uppercase; letter-spacing: 0.05em;">Memberships</div>
                    <div style="font-size: 11px; color: {T['text_muted']}; font-weight: 600;">Club Marriott • Prime • Swiggy</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 2. Quarterly Milestone
q_bonus = data["milestones"]["quarterly"]
with m_col2:
    q_tag = "✅ UNLOCKED" if q_bonus["met"] else f"⏳ {q_bonus['days_left']}d left"
    q_class = "pill-green" if q_bonus["met"] else "pill-orange"
    st.markdown(
        f"""
        <div class="metal-card" style="min-height: 236px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <div style="font-size: 12px; font-weight: 700; color: {T['text_muted']}; text-transform: uppercase;">Quarterly Bonus ({q_bonus['label']})</div>
                        <div style="font-size: 16px; font-weight: 700; color: {T['text_main']};">10,000 Bonus RP</div>
                    </div>
                    <span class="pill {q_class}">{q_tag}</span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: {'#b45309' if is_light else '#f59e0b'}; margin: 6px 0;">
                    ₹{q_bonus["spend"]:,.0f} <span style="font-size: 14px; font-weight: 500; color: {T['text_sub']};">/ ₹{q_bonus["target"]:,.0f}</span>
                    <span style="font-size: 13px; font-weight: 700; color: {'#b45309' if is_light else '#fbbf24'}; margin-left: 6px;">({q_bonus['progress']}%)</span>
                </div>
                <div style="background: {T['progress_bg']}; border-radius: 999px; height: 8px; margin: 8px 0; overflow: hidden;">
                    <div style="background: {'#b45309' if is_light else '#f59e0b'}; width: {q_bonus['progress']}%; height: 100%;"></div>
                </div>
            </div>
            <div style="background: {T['subcard_bg']}; border: 1px solid {T['subcard_border']}; border-radius: 10px; padding: 9px 12px; display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                <div>
                    <div style="font-size: 10px; font-weight: 700; color: {T['text_sub']}; text-transform: uppercase; letter-spacing: 0.05em;">Remaining Needed</div>
                    <div style="font-size: 15px; font-weight: 800; color: {'#b45309' if is_light else '#fbbf24'}; letter-spacing: -0.01em;">₹{q_bonus['remaining']:,.0f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 10px; font-weight: 700; color: {T['text_sub']}; text-transform: uppercase; letter-spacing: 0.05em;">Run-Rate Needed</div>
                    <div style="font-size: 11px; color: {T['text_muted']};"><b>₹{q_bonus['daily_runrate_needed']:,.0f}</b> / day</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 3. Annual Fee Waiver
annual = data["milestones"]["annual_waiver"]
with m_col3:
    ann_tag = "✅ WAIVED" if annual["met"] else f"⏳ {annual['days_left']}d left"
    ann_class = "pill-green" if annual["met"] else "pill-blue"
    st.markdown(
        f"""
        <div class="metal-card" style="min-height: 236px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <div style="font-size: 12px; font-weight: 700; color: {T['text_muted']}; text-transform: uppercase;">Annual Fee Waiver</div>
                        <div style="font-size: 16px; font-weight: 700; color: {T['text_main']};">Save ₹10,000 Fee</div>
                    </div>
                    <span class="pill {ann_class}">{ann_tag}</span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: {'#9a6014' if is_light else '#38bdf8'}; margin: 6px 0;">
                    ₹{annual["spend"]:,.0f} <span style="font-size: 14px; font-weight: 500; color: {T['text_sub']};">/ ₹{annual["target"]:,.0f}</span>
                    <span style="font-size: 13px; font-weight: 700; color: {'#9a6014' if is_light else '#38bdf8'}; margin-left: 6px;">({annual['progress']}%)</span>
                </div>
                <div style="background: {T['progress_bg']}; border-radius: 999px; height: 8px; margin: 8px 0; overflow: hidden;">
                    <div style="background: {'#9a6014' if is_light else '#38bdf8'}; width: {annual['progress']}%; height: 100%;"></div>
                </div>
            </div>
            <div style="background: {T['subcard_bg']}; border: 1px solid {T['subcard_border']}; border-radius: 10px; padding: 9px 12px; display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                <div>
                    <div style="font-size: 10px; font-weight: 700; color: {T['text_sub']}; text-transform: uppercase; letter-spacing: 0.05em;">Remaining to Waive</div>
                    <div style="font-size: 15px; font-weight: 800; color: {'#9a6014' if is_light else '#38bdf8'}; letter-spacing: -0.01em;">₹{annual['remaining']:,.0f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 10px; font-weight: 700; color: {T['text_sub']}; text-transform: uppercase; letter-spacing: 0.05em;">Deadline</div>
                    <div style="font-size: 11px; color: {T['text_muted']};"><b>{annual['period_end']}</b> ({annual['days_left']}d left)</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─── SECTION 3: INTERACTIVE TABS (HISTORY, LEDGER & REDEMPTIONS) ──────────────
tab_history, tab_ledger, tab_redemptions = st.tabs([
    "📊 Monthly History & Caps",
    "📋 Live Transactions",
    "🎟️ Points Redemptions",
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
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    with st.expander("🔍 View Itemized Transactions for a Specific Month"):
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
        st.markdown(
            f"""
            <div style="display: flex; gap: 12px; flex-wrap: wrap; margin: 12px 0 16px 0;">
                <div style="background: {T['chip_bg']}; border: 1px solid {T['chip_border']}; padding: 8px 14px; border-radius: 10px;">
                    <span style="font-size: 11px; color: {T['text_muted']}; font-weight: 600;">COUNT:</span>
                    <span style="font-size: 14px; font-weight: 800; color: {T['text_main']}; margin-left: 6px;">{len(tx_list)}</span>
                </div>
                <div style="background: {T['chip_bg']}; border: 1px solid {T['chip_border']}; padding: 8px 14px; border-radius: 10px;">
                    <span style="font-size: 11px; color: {T['text_muted']}; font-weight: 600;">FILTERED SPEND:</span>
                    <span style="font-size: 14px; font-weight: 800; color: {'#9a6014' if is_light else '#38bdf8'}; margin-left: 6px;">₹{total_filtered_spend:,.2f}</span>
                </div>
                <div style="background: {T['chip_bg']}; border: 1px solid {T['chip_border']}; padding: 8px 14px; border-radius: 10px;">
                    <span style="font-size: 11px; color: {T['text_muted']}; font-weight: 600;">BASE RP:</span>
                    <span style="font-size: 14px; font-weight: 800; color: {'#784708' if is_light else '#93c5fd'}; margin-left: 6px;">{total_filtered_base:,} RP</span>
                </div>
                <div style="background: {T['chip_bg']}; border: 1px solid {T['chip_border']}; padding: 8px 14px; border-radius: 10px;">
                    <span style="font-size: 11px; color: {T['text_muted']}; font-weight: 600;">ACCELERATED RP:</span>
                    <span style="font-size: 14px; font-weight: 800; color: {'#b45309' if is_light else '#a78bfa'}; margin-left: 6px;">{total_filtered_acc:,} RP</span>
                </div>
                <div style="background: {T['chip_bg']}; border: 1px solid {T['chip_border']}; padding: 8px 14px; border-radius: 10px;">
                    <span style="font-size: 11px; color: {T['text_muted']}; font-weight: 600;">TOTAL RP:</span>
                    <span style="font-size: 14px; font-weight: 800; color: {'#15803d' if is_light else '#10b981'}; margin-left: 6px;">{total_filtered_rp:,} RP</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
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
                label="📥 Export",
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

    st.markdown(
        f"""
        <div style="background: {T['subcard_bg']}; border: 1px solid {T['subcard_border']}; border-radius: 12px; padding: 14px 20px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <span style="font-size: 11px; color: {T['text_muted']}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;">Points Burned:</span>
                <span style="font-size: 16px; font-weight: 800; color: {'#b45309' if is_light else '#fbbf24'}; margin-left: 6px;">{total_pts_burned:,} RP</span>
            </div>
            <div>
                <span style="font-size: 11px; color: {T['text_muted']}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;">Direct Savings:</span>
                <span style="font-size: 16px; font-weight: 800; color: {'#15803d' if is_light else '#34d399'}; margin-left: 6px;">₹{total_saved:,.0f}</span>
            </div>
            <div>
                <span style="font-size: 11px; color: {T['text_muted']}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;">Total Booking Value:</span>
                <span style="font-size: 16px; font-weight: 800; color: {T['text_main']}; margin-left: 6px;">₹{total_fare:,.0f}</span>
            </div>
            <div>
                <span style="font-size: 11px; color: {T['text_muted']}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;">Cash Paid (DCBM):</span>
                <span style="font-size: 16px; font-weight: 800; color: {'#9a6014' if is_light else '#38bdf8'}; margin-left: 6px;">₹{total_cash:,.0f}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
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
st.markdown(
    f"""
    <div style="text-align: center; font-size: 12px; color: {T['footer_text']}; margin-top: 30px; border-top: 1px solid {T['footer_border']}; padding-top: 15px;">
        HDFC Diners Club Black Metal Dashboard • Automated via Gmail Alerts • Built for Ejaz Anwar
    </div>
    """,
    unsafe_allow_html=True,
)
