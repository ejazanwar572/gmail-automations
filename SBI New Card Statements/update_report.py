#!/usr/bin/env python3
from pathlib import Path
import phonepe_tracker

if __name__ == "__main__":
    print(phonepe_tracker.write_outputs(Path(__file__).resolve().parent))
