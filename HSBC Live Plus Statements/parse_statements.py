#!/usr/bin/env python3
from pathlib import Path
import json
import hsbc_engine

if __name__ == "__main__":
    payload = hsbc_engine.build_statements_data(Path(__file__).resolve().parent)
    print(json.dumps({"ok": True, "transactions": len(payload.get("transactions", []))}, indent=2, sort_keys=True))
