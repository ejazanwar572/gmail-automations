#!/usr/bin/env python3
from pathlib import Path
import dcbm_engine

if __name__ == "__main__":
    path = dcbm_engine.write_report(Path(__file__).resolve().parent)
    print(path)
