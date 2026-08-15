#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import card_benefit_tracker as tracker

if __name__ == "__main__":
    payload = tracker.build_statements_data(Path(__file__).resolve().parent)
    print(json.dumps({"ok": True, "transactions": len(payload.get("transactions", []))}, indent=2, sort_keys=True))
