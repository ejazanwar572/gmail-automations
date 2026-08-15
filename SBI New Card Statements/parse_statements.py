#!/usr/bin/env python3
from pathlib import Path
import json

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    path = root / "statements_data.json"
    payload = json.loads(path.read_text()) if path.exists() else {}
    payload.setdefault("posted_reward_points", 0)
    payload.setdefault("reward_reconciled", False)
    payload.setdefault("welcome_voucher_received", False)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "statements": len(payload.get("statements", []))}, indent=2))
