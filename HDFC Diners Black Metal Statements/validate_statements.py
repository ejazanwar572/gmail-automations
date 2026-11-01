#!/usr/bin/env python3
from pathlib import Path
import dcbm_engine

if __name__ == "__main__":
    result = dcbm_engine.validate_card_dir(Path(__file__).resolve().parent)
    raise SystemExit(dcbm_engine.print_validation(result))
