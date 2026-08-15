#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import card_benefit_tracker as tracker

if __name__ == "__main__":
    result = tracker.sync_from_step_logs(Path(__file__).resolve().parent)
    print(json.dumps(result, indent=2, sort_keys=True))
