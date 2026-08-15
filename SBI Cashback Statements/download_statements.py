#!/usr/bin/env python3
"""
Download SBI Cashback monthly statement PDFs from Gmail using readonly API access.
"""

import base64
import os
import re

from sync_alerts import get_gmail_service


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
QUERY = 'from:Statements@sbicard.com subject:"Your CASHBACK SBI Card Monthly Statement"'
MONTHS = {
    "Jan": "January",
    "Feb": "February",
    "Mar": "March",
    "Apr": "April",
    "May": "May",
    "Jun": "June",
    "Jul": "July",
    "Aug": "August",
    "Sep": "September",
    "Oct": "October",
    "Nov": "November",
    "Dec": "December",
}


def iter_parts(payload):
    for part in payload.get("parts", []):
        yield part
        yield from iter_parts(part)


def filename_from_subject(subject):
    match = re.search(r"Monthly Statement\s*-?\s*([A-Za-z]{3})\s+(\d{4})", subject)
    if not match:
        return None
    month = MONTHS.get(match.group(1).title())
    if not month:
        return None
    return f"SBI_Cashback_Statement_{month}_{match.group(2)}.pdf"


def main():
    service = get_gmail_service()
    if not service:
        raise SystemExit("Could not load Gmail readonly service.")

    downloaded = 0
    skipped = 0
    page_token = None
    while True:
        response = service.users().messages().list(
            userId="me",
            q=QUERY,
            maxResults=100,
            pageToken=page_token,
        ).execute()
        for item in response.get("messages", []):
            message = service.users().messages().get(
                userId="me",
                id=item["id"],
                format="full",
            ).execute()
            payload = message.get("payload", {})
            headers = {h.get("name", "").lower(): h.get("value", "") for h in payload.get("headers", [])}
            subject = headers.get("subject", "")
            target_name = filename_from_subject(subject)
            if not target_name:
                skipped += 1
                continue
            target_path = os.path.join(SCRIPT_DIR, target_name)
            if os.path.exists(target_path):
                skipped += 1
                continue

            for part in iter_parts(payload):
                body = part.get("body", {})
                attachment_id = body.get("attachmentId")
                source_name = part.get("filename", "")
                if not attachment_id or not source_name.lower().endswith(".pdf"):
                    continue
                attachment = service.users().messages().attachments().get(
                    userId="me",
                    messageId=item["id"],
                    id=attachment_id,
                ).execute()
                data = base64.urlsafe_b64decode(attachment["data"].encode("utf-8"))
                with open(target_path, "wb") as f:
                    f.write(data)
                downloaded += 1
                print(f"Downloaded {target_name} from {source_name}")
                break

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    print(f"Finished SBI statement backfill: {downloaded} downloaded, {skipped} skipped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"SBI statement backfill blocked: {exc}")
