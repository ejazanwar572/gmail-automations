"""
Streamlit Cloud Entrypoint for HDFC Diners Club Black Metal Control Center.
Delegates cleanly to 'HDFC Diners Black Metal Statements/hdfc_dcbm_app.py'.
"""
from pathlib import Path
import runpy
import sys

# Add card folder to module path
card_dir = Path(__file__).resolve().parent / "HDFC Diners Black Metal Statements"
sys.path.insert(0, str(card_dir))

# Execute main dashboard
app_path = card_dir / "hdfc_dcbm_app.py"
runpy.run_path(str(app_path), run_name="__main__")
