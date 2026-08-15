#!/usr/bin/env python3
from pathlib import Path
import argparse
import subprocess
import sys

TAIL = ["parse_statements.py", "validate_statements.py", "update_report.py"]
SYNC_SCRIPTS = {"gmail-api": "sync_alerts.py", "mcp-step-logs": "sync_gmail_mcp.py"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run this card benefit workflow.")
    parser.add_argument(
        "--sync-source",
        choices=("gmail-api", "mcp-step-logs", "none"),
        default="gmail-api",
    )
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    scripts = ([SYNC_SCRIPTS[args.sync_source]] if args.sync_source != "none" else []) + TAIL
    for script in scripts:
        completed = subprocess.run([sys.executable, str(here / script)], cwd=str(here), text=True)
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
