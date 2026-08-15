#!/usr/bin/env python3
from pathlib import Path
import json
import phonepe_tracker

if __name__ == "__main__":
    result = phonepe_tracker.validate(Path(__file__).resolve().parent)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)
