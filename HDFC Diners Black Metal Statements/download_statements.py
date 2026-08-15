#!/usr/bin/env python3
from pathlib import Path
import json

if __name__ == "__main__":
    payload = {"ok": True, "downloaded": 0, "message": "No statement PDFs configured for automatic download yet."}
    path = Path(__file__).resolve().parent / "statement_download_report.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
