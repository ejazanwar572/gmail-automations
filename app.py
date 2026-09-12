"""
Credit Card Control Center - Multi-Card Hub.
Seamlessly routes between HDFC Diners Club Black Metal and HSBC Live+.
"""
from pathlib import Path
import runpy
import sys
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
HDFC_DIR = ROOT_DIR / "HDFC Diners Black Metal Statements"
HSBC_DIR = ROOT_DIR / "HSBC Live Plus Statements"

sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(HDFC_DIR))
sys.path.insert(0, str(HSBC_DIR))

# Default to HSBC Live+ on this feature branch
if "selected_card" not in st.session_state:
    st.session_state["selected_card"] = "HSBC Live+ Credit Card"

# Safe page config (sets initial browser tab metadata)
try:
    if "HSBC" in st.session_state["selected_card"]:
        st.set_page_config(
            page_title="HSBC Live+ | Control Center",
            page_icon="💳",
            layout="wide",
            initial_sidebar_state="collapsed",
        )
    else:
        st.set_page_config(
            page_title="HDFC Diners Black Metal | Control Center",
            page_icon="💳",
            layout="wide",
            initial_sidebar_state="collapsed",
        )
except Exception:
    pass

selected_card = st.session_state.get("selected_card", "HSBC Live+ Credit Card")

if "HSBC" in selected_card:
    hsbc_app_path = HSBC_DIR / "hsbc_live_plus_app.py"
    runpy.run_path(str(hsbc_app_path), run_name="__main__")
else:
    hdfc_app_path = HDFC_DIR / "hdfc_dcbm_app.py"
    runpy.run_path(str(hdfc_app_path), run_name="__main__")
