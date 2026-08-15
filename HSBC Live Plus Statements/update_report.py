#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import card_benefit_tracker as tracker

if __name__ == "__main__":
    path = tracker.write_report(Path(__file__).resolve().parent)
    print(path)
