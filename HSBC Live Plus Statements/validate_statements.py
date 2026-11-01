#!/usr/bin/env python3
from pathlib import Path
import hsbc_engine

if __name__ == "__main__":
    result = hsbc_engine.validate_card_dir(Path(__file__).resolve().parent)
    raise SystemExit(hsbc_engine.print_validation(result))
