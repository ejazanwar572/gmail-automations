#!/usr/bin/env python3
"""
Automatically download HDFC Diners Club Black Metal statement PDFs from Gmail.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List

from sync_alerts import build_service, SyncError


QUERY = 'from:Emailstatements.cards@hdfcbank.bank.in "Diners Black" -in:trash -in:spam'


def download_statements(card_dir: Path | str) -> Dict[str, Any]:
    card_dir = Path(card_dir)
    try:
        service = build_service(card_dir)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "downloaded": 0}

    try:
        res = service.users().messages().list(userId="me", q=QUERY).execute()
    except Exception as exc:
        return {"ok": False, "error": f"Failed to list statement messages: {exc}", "downloaded": 0}

    messages: List[Dict[str, Any]] = res.get("messages", [])
    downloaded_files: List[str] = []

    for m in messages:
        try:
            msg = service.users().messages().get(userId="me", id=m["id"]).execute()
            payload = msg.get("payload", {})
            parts = payload.get("parts", [])
            for part in parts:
                filename = part.get("filename", "")
                if filename.endswith(".pdf") and "0036" in filename:
                    date_match = re.search(r"(\d{2})-(\d{2})-(\d{4})", filename)
                    if not date_match:
                        continue
                    d, mth, y = date_match.groups()
                    target_name = f"statement_{y}_{mth}_{d}.pdf"
                    target_path = card_dir / target_name

                    if target_path.exists():
                        continue

                    # Download attachment
                    attachment_id = part.get("body", {}).get("attachmentId")
                    if not attachment_id:
                        continue

                    att = service.users().messages().attachments().get(
                        userId="me", messageId=m["id"], id=attachment_id
                    ).execute()
                    data = att.get("data", "")
                    if data:
                        file_bytes = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
                        target_path.write_bytes(file_bytes)
                        downloaded_files.append(target_name)
        except Exception as e:
            print(f"Warning: could not process statement message {m.get('id')}: {e}")

    report = {
        "ok": True,
        "downloaded_count": len(downloaded_files),
        "downloaded_files": downloaded_files,
        "total_emails_found": len(messages),
    }

    report_path = card_dir / "statement_download_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    card_dir = Path(__file__).resolve().parent
    result = download_statements(card_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
