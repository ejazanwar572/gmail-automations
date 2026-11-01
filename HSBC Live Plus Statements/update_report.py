#!/usr/bin/env python3
from pathlib import Path
import hsbc_engine

if __name__ == "__main__":
    path = hsbc_engine.write_report(Path(__file__).resolve().parent)
    print(path)
