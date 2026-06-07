#!/usr/bin/env python3
"""
Unified workflow script for SBI Cashback Card calculations.
Executes the sync, validation, and report updates in sequence.
"""

import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SYNC_SCRIPT = os.path.join(SCRIPT_DIR, "sync_alerts.py")
VALIDATE_SCRIPT = os.path.join(SCRIPT_DIR, "validate_statements.py")
UPDATE_SCRIPT = os.path.join(SCRIPT_DIR, "update_report.py")
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "credentials.json")

def run_step(name, script_path, run_condition=True):
    """Helper to execute a step in the workflow."""
    if not run_condition:
        print(f"\n⏭️  Skipping Step: {name}")
        return True

    print(f"\n🚀 Running Step: {name} ({os.path.basename(script_path)})...")
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            text=True
        )
        print(f"✅ Step Complete: {name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Step Failed: {name} (Exit code {e.returncode})")
        return False
    except Exception as e:
        print(f"❌ Unexpected error executing {name}: {e}")
        return False

def main():
    print("=" * 70)
    print("      SBI CASHBACK CARD TRACKER — WORKFLOW RUNNER")
    print("=" * 70)

    # 1. Sync Gmail Alerts
    has_creds = os.path.exists(CREDENTIALS_FILE)
    if not has_creds:
        print("\nℹ️  Note: 'credentials.json' not found locally.")
        print("   Skipping Gmail API sync. (The report will be updated using existing alerts cache).")
        print("   To enable sync, place your Google API 'credentials.json' in this directory.")
    
    sync_ok = run_step("Sync Gmail Alerts", SYNC_SCRIPT, run_condition=has_creds)
    if not sync_ok:
        print("\n⚠️  Workflow halted due to sync failure.")
        sys.exit(1)

    # 2. Run Statement Validations
    val_ok = run_step("Validate Statement PDFs", VALIDATE_SCRIPT)
    if not val_ok:
        print("\n⚠️  Workflow warning: Statement validation checks encountered issues.")

    # 3. Update Markdown Report
    update_ok = run_step("Regenerate Cashback Cap Report", UPDATE_SCRIPT)
    if not update_ok:
        print("\n❌ Workflow failed: Could not regenerate cashback report.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("🎉 WORKFLOW RUN COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
