#!/usr/bin/env python3
"""Download PhonePe SBI statement PDFs and retain issuer password instructions."""
import base64
import json
from pathlib import Path
from sync_alerts import build_service, _body, _headers

ROOT = Path(__file__).resolve().parent
QUERY = 'from:statements@sbicard.com ("PhonePe" OR "ending 3366" OR "XX3366") has:attachment filename:pdf'

def parts(payload):
    for item in payload.get("parts", []):
        yield item
        yield from parts(item)

if __name__ == "__main__":
    try:
        service = build_service(); api = service.users().messages(); token = None; downloaded = 0; instructions = []
        while True:
            page = api.list(userId="me", q=QUERY, maxResults=100, pageToken=token).execute()
            for item in page.get("messages", []):
                message = api.get(userId="me", id=item["id"], format="full").execute(); payload = message.get("payload", {}); headers = _headers(payload)
                instructions.append({"message_id": item["id"], "subject": headers.get("subject", ""), "password_instructions": " ".join(_body(payload).split())})
                for part in parts(payload):
                    attachment_id = part.get("body", {}).get("attachmentId")
                    if not attachment_id or not part.get("filename", "").lower().endswith(".pdf"): continue
                    data = api.attachments().get(userId="me", messageId=item["id"], id=attachment_id).execute()["data"]
                    target = ROOT / f"PhonePe_SBI_Statement_{item['id']}.pdf"
                    if not target.exists(): target.write_bytes(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))); downloaded += 1
            token = page.get("nextPageToken")
            if not token: break
        (ROOT / "statement_password_instructions.json").write_text(json.dumps(instructions, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"ok": True, "downloaded": downloaded, "statements": len(instructions)}, indent=2))
    except Exception as exc:
        print(f"PhonePe SBI statement download failed: {exc}", file=__import__("sys").stderr); raise SystemExit(1)
