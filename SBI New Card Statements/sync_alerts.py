#!/usr/bin/env python3
"""Read-only Gmail transaction sync for PhonePe SBI SELECT BLACK ending 3366."""

from __future__ import annotations
import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
QUERY = 'from:onlinesbicard@sbicard.com subject:"Transaction Alert from PhonePe SBI card SELECT BLACK" -in:trash -in:spam'
RECEIPT_QUERY = 'from:noreply@phonepe.com subject:("is successful") -in:trash -in:spam'
ROOT = Path(__file__).resolve().parent
SHARED_TOKEN = Path("/Users/ejazanwar/.gmail-mcp/credentials.json")
SHARED_KEYS = Path("/Users/ejazanwar/.gmail-mcp/gcp-oauth.keys.json")
PAGE_LIMIT = 50

class SyncError(RuntimeError): pass

def _decode(value): return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode("utf-8", "replace")
def _body(payload):
    texts = []
    def walk(part):
        data = part.get("body", {}).get("data")
        if data and part.get("mimeType") in ("text/plain", "text/html"): texts.append(_decode(data))
        for child in part.get("parts", []): walk(child)
    walk(payload)
    return unescape(re.sub(r"<[^>]+>", " ", " ".join(texts)))
def _headers(payload): return {item.get("name", "").lower(): item.get("value", "") for item in payload.get("headers", [])}

def classify(merchant, body):
    text = f"{merchant} {body}".upper()
    # An SBI alert saying "via UPI" does not identify the UPI app. Keep it
    # pending until matching PhonePe evidence proves the correct reward route.
    if "VIA UPI" in text and "PHONEPE" not in merchant.upper(): return "pending"
    if "PHONEPE" in text and "INSURANCE" in text: return "insurance"
    if "PHONEPE" in text: return "phonepe"
    if any(token in text for token in ("AMAZON", "FLIPKART", "SWIGGY", "ZOMATO", "MYNTRA", "NYKAA", "BOOKMYSHOW", "MAKEMYTRIP", "BLINKIT", "ZEPTO", "RAPIDO", "UBER")): return "online"
    return "other"

def parse_phonepe_receipt(headers, body):
    subject = headers.get("subject", "")
    match = re.search(r"Payment\s+(?:for|to)\s+(.*?)\s+of\s+[₹Rs. ]+([\d,]+(?:\.\d{1,2})?)\s+is successful", subject, re.I)
    if not match:
        return None
    try:
        email_date = parsedate_to_datetime(headers.get("date", "")).date().isoformat()
    except (TypeError, ValueError):
        return None
    return {
        "date": email_date,
        "amount": float(match.group(2).replace(",", "")),
        "description": match.group(1).strip(),
    }

def _receipt_category(description):
    text = description.upper()
    if "INSURANCE" in text:
        return "insurance"
    if any(token in text for token in (
        "RECHARGE", "MOBILE", "PREPAID", "POSTPAID", "DTH", "BILL", "ELECTRIC",
        "BROADBAND", "LANDLINE", "GAS", "WATER", "FLIGHT", "HOTEL", "TRAVEL",
    )):
        return "phonepe"
    return "other"

def apply_phonepe_receipts(alerts, receipts):
    unused = set(range(len(receipts)))
    for alert in alerts:
        if alert.get("category") != "pending":
            continue
        match_index = next((
            index for index in sorted(unused)
            if receipts[index].get("date") == alert.get("date")
            and abs(float(receipts[index].get("amount", 0)) - float(alert.get("amount", 0))) < 0.005
        ), None)
        if match_index is None:
            continue
        receipt = receipts[match_index]
        unused.remove(match_index)
        alert["category"] = _receipt_category(receipt.get("description", ""))
        alert["classification_evidence"] = "phonepe-receipt"
        alert["phonepe_receipt_message_id"] = receipt.get("message_id")
    for alert in alerts:
        if alert.get("category") == "pending":
            alert["category"] = "other"
            alert["classification_evidence"] = "user-approved-phonepe-upi-assumption"
    return alerts

def parse(body):
    text = " ".join(body.split())
    patterns = (
        r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)\s+spent on your SBI Credit Card ending with 3366 at (.*?)\s+on\s+(\d{1,2}-\d{1,2}-\d{2,4})",
        r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)\s+spent on your SBI Credit Card ending 3366 at (.*?)\s+on\s+(\d{1,2}/\d{1,2}/\d{2,4})",
        r"Trxn\.\s+of\s+Rs\.?\s*([\d,]+(?:\.\d{1,2})?)\s+done\s+on\s+your\s+credit\s+card\s+ending\s+3366.*?\bat\s+(.*?)\s+on\s+(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})",
    )
    match = next((candidate for pattern in patterns if (candidate := re.search(pattern, text, re.I))), None)
    if not match: raise SyncError("a matching transaction alert could not be parsed")
    raw = match.group(3)
    parsed = None
    for fmt in ("%d-%m-%y", "%d-%m-%Y", "%d/%m/%y", "%d/%m/%Y", "%d %b %y", "%d %B %y", "%d %b %Y", "%d %B %Y"):
        try: parsed = datetime.strptime(raw, fmt).date(); break
        except ValueError: pass
    if not parsed: raise SyncError("transaction date could not be parsed")
    merchant = match.group(2).strip()
    return {"date": parsed.isoformat(), "amount": float(match.group(1).replace(",", "")), "merchant": merchant, "category": classify(merchant, text)}

def build_service():
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        token = json.loads(SHARED_TOKEN.read_text()); keys = json.loads(SHARED_KEYS.read_text())["installed"]
        scopes = token.get("scope", SCOPES); scopes = scopes.split() if isinstance(scopes, str) else scopes
        credentials = Credentials(token=token["access_token"], refresh_token=token["refresh_token"], token_uri="https://oauth2.googleapis.com/token", client_id=keys["client_id"], client_secret=keys["client_secret"], scopes=scopes)
        if credentials.expired: credentials.refresh(Request())
        if not credentials.valid: raise SyncError("Gmail credentials are invalid")
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)
    except SyncError: raise
    except Exception as exc: raise SyncError("Gmail authentication failed") from exc

def sync(service):
    api = service.users().messages(); ids = []; token = None; pages = 0
    try:
        while True:
            pages += 1
            if pages > PAGE_LIMIT: raise SyncError("Gmail pagination safety ceiling reached")
            response = api.list(userId="me", q=QUERY, maxResults=100, pageToken=token).execute()
            ids.extend(item["id"] for item in response.get("messages", [])); token = response.get("nextPageToken")
            if not token: break
        ids = list(dict.fromkeys(ids)); alerts = []
        for message_id in ids:
            message = api.get(userId="me", id=message_id, format="full").execute(); payload = message.get("payload", {}); headers = _headers(payload)
            alert = parse(_body(payload)); alert.update({"message_id": message_id, "subject": headers.get("subject", ""), "email_date": headers.get("date", ""), "source": "gmail-api"}); alerts.append(alert)
        receipt_ids = []; token = None; pages = 0
        while True:
            pages += 1
            if pages > PAGE_LIMIT: raise SyncError("PhonePe receipt pagination safety ceiling reached")
            response = api.list(userId="me", q=RECEIPT_QUERY, maxResults=100, pageToken=token).execute()
            receipt_ids.extend(item["id"] for item in response.get("messages", [])); token = response.get("nextPageToken")
            if not token: break
        receipt_ids = list(dict.fromkeys(receipt_ids)); receipts = []
        for message_id in receipt_ids:
            message = api.get(userId="me", id=message_id, format="full").execute(); payload = message.get("payload", {}); headers = _headers(payload)
            receipt = parse_phonepe_receipt(headers, _body(payload))
            if receipt:
                receipt["message_id"] = message_id
                receipts.append(receipt)
        apply_phonepe_receipts(alerts, receipts)
    except SyncError: raise
    except Exception as exc: raise SyncError("Gmail API retrieval failed") from exc
    alerts.sort(key=lambda item: (item["date"], item["message_id"])); run_id = str(uuid.uuid4())
    metadata = {"source": "gmail-api", "query": QUERY, "receipt_query": RECEIPT_QUERY, "upi_classification_assumption": "All UPI transactions on card 3366 are made through PhonePe unless receipt evidence proves a more specific PhonePe category", "card_name": "PhonePe SBI Card SELECT BLACK", "card_ending": "3366", "run_id": run_id, "alert_count": len(alerts), "unique_alert_count": len(alerts), "parsed_count": len(alerts), "message_ids_seen": ids, "phonepe_receipt_count": len(receipts), "phonepe_receipt_message_ids_seen": receipt_ids, "latest_alert_date": max((item["date"] for item in alerts), default=datetime.now().date().isoformat()), "cached_total": round(sum(item["amount"] for item in alerts), 2), "skipped_duplicate_count": 0, "synced_at": datetime.now(timezone.utc).isoformat()}
    for filename, payload in (("gmail_alerts.json", alerts), ("sync_metadata.json", metadata)):
        fd, name = tempfile.mkstemp(prefix=f".{filename}.", suffix=".tmp", dir=ROOT)
        with os.fdopen(fd, "w") as handle: json.dump(payload, handle, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(name, ROOT / filename)
    return metadata

if __name__ == "__main__":
    try: print(json.dumps(sync(build_service()), indent=2, sort_keys=True))
    except SyncError as exc: print(f"PhonePe SBI Gmail sync failed: {exc}", file=__import__("sys").stderr); raise SystemExit(1)
