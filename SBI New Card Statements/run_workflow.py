#!/usr/bin/env python3
from pathlib import Path
import argparse
import subprocess
import sys

TAIL = ["download_statements.py", "parse_statements.py", "validate_statements.py", "update_report.py"]
SYNC = {"gmail-api": "sync_alerts.py", "mcp-step-logs": "sync_gmail_mcp.py"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync-source", choices=("gmail-api", "mcp-step-logs", "none"), default="gmail-api")
    source = parser.parse_args().sync_source
    scripts = ([SYNC[source]] if source != "none" else []) + TAIL
    root = Path(__file__).resolve().parent
    for script in scripts:
        result = subprocess.run([sys.executable, str(root / script)], cwd=root, text=True)
        if result.returncode:
            raise SystemExit(result.returncode)
