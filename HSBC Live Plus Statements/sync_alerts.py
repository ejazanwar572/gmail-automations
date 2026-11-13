#!/usr/bin/env python3
"""Read HSBC transaction alerts from Gmail without interactive authentication."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import uuid

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import alert_ingestion as shared
from alert_ingestion import (
    SCOPES,
    SHARED_KEYS,
    SHARED_TOKEN,
    SyncError,
    build_service,
    decode_message_body,
    get_email_date as _email_date,
    get_header as _header,
    load_credentials,
    write_temp_file,
)

TRANSACTION_SUBJECT = "You have used your HSBC Credit Card ending with 8690 for a purchase transaction"
TRANSACTION_SUBJECT_NEW = "Credit Card Transaction Alert"
TRANSACTION_SUBJECTS = {TRANSACTION_SUBJECT, TRANSACTION_SUBJECT_NEW}
QUERY = f'(subject:"{TRANSACTION_SUBJECT_NEW}" OR subject:"{TRANSACTION_SUBJECT}") -in:spam -in:trash'
CARD_NAME = "HSBC Live+ Credit Card"
CARD_ENDING = "8690"


def _decode(data: str) -> str:
    return shared.decode_base64_urlsafe(data)


def _parts(payload: dict, mime: str):
    return shared.iter_mime_parts(payload, mime)


def is_hard_filtered_candidate(text: str) -> bool:
    normalized = " ".join(text.split())
    if re.search(r"Credit card no ending with 8690\s*,?\s*has been used for INR\s+", normalized, re.IGNORECASE):
        return True
    if re.search(r"HSBC Credit Card xx8690 was used for a transaction of INR\s+", normalized, re.IGNORECASE):
        return True
    return False


def is_transaction_subject(subject: str) -> bool:
    """Identify the HSBC purchase-alert subjects for card 8690."""
    return subject.strip() in TRANSACTION_SUBJECTS


def parse_transaction(text: str) -> dict[str, str | float]:
    normalized = " ".join(text.split())
    # Format 1: classic format
    match = re.search(
        r"Credit card no ending with 8690\s*,?\s*has been used for INR\s+"
        r"(?P<amount>\d[\d,]*\.\d{2})\s+for payment to\s+"
        r"(?P<merchant>.+?)\s+on\s+(?P<date>\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+at\s+\d{1,2}:\d{2}",
        normalized, re.IGNORECASE,
    )
    if match:
        try:
            date_str = datetime.strptime(match.group("date"), "%d %b %Y").date().isoformat()
        except ValueError as exc:
            raise SyncError("HSBC transaction date could not be parsed") from exc
        return {
            "date": date_str,
            "merchant": match.group("merchant").strip(),
            "amount": float(match.group("amount").replace(",", "")),
        }

    # Format 2: new format (starting August 2026)
    match_new = re.search(
        r"HSBC Credit Card xx8690 was used for a transaction of INR\s+"
        r"(?P<amount>\d[\d,]*\.\d{2})\s+at\s+"
        r"(?P<merchant>.+?)\s+on\s+(?P<date>\d{1,2}/\d{1,2}/\d{2,4})",
        normalized, re.IGNORECASE,
    )
    if match_new:
        raw_date = match_new.group("date")
        try:
            parts = raw_date.split("/")
            fmt = "%d/%m/%Y" if len(parts[-1]) == 4 else "%d/%m/%y"
            date_str = datetime.strptime(raw_date, fmt).date().isoformat()
        except ValueError as exc:
            raise SyncError("HSBC transaction date could not be parsed") from exc
        return {
            "date": date_str,
            "merchant": match_new.group("merchant").strip(),
            "amount": float(match_new.group("amount").replace(",", "")),
        }

    raise SyncError("hard-filtered HSBC transaction alert could not be parsed")


def credential_paths(root: Path, shared_token: Path = SHARED_TOKEN,
                     shared_keys: Path = SHARED_KEYS) -> tuple[Path, Path]:
    local = root / "token.json"
    if local.exists():
        return local, local
    return shared_token, shared_keys


def _write_json_temp(root: Path, target: str, value) -> Path:
    return write_temp_file(root, target, value, binary=False)


def _write_bytes_temp(root: Path, target: str, value: bytes) -> Path:
    return write_temp_file(root, target, value, binary=True)


def sync(service, root: Path, *, run_id: str | None = None) -> dict:
    run_id = run_id or str(uuid.uuid4())
    try:
        adapter = shared.GmailApiAdapter(service)
        ids, messages = adapter.fetch_messages_for_query(QUERY)
        unique_ids = list(dict.fromkeys(ids))
    except Exception as exc:
        raise SyncError("Gmail API retrieval failed") from exc

    alerts, rejected, matched = {}, 0, 0
    for message in messages:
        subject = _header(message, "Subject")
        if not is_transaction_subject(subject):
            rejected += 1
            continue
        body = decode_message_body(message.get("payload", {}))
        if subject == TRANSACTION_SUBJECT_NEW and "8690" not in body:
            rejected += 1
            continue
        matched += 1
        parsed = parse_transaction(body)
        message_id = message["id"]
        alerts[message_id] = {
            **parsed,
            "subject": subject,
            "message_id": message_id,
            "email_date": _email_date(message),
            "source": "gmail-api",
        }
    ordered = sorted(alerts.values(), key=lambda item: (item["date"], item["message_id"]))
    alerts_path, metadata_path = root / "gmail_alerts.json", root / "sync_metadata.json"
    previous_bytes = alerts_path.read_bytes() if alerts_path.exists() else None
    previous_metadata_bytes = metadata_path.read_bytes() if metadata_path.exists() else None
    previous_count = 0
    if previous_bytes is not None:
        try:
            previous = json.loads(previous_bytes)
            previous_count = len(previous) if isinstance(previous, list) else 0
        except (json.JSONDecodeError, TypeError):
            previous_count = 0
    now = datetime.now(timezone.utc).isoformat()
    metadata = {
        "synced_at": now, "source": "gmail-api", "query": QUERY,
        "card_name": CARD_NAME, "card_ending": CARD_ENDING,
        "alert_count": len(ordered), "unique_alert_count": len(ordered),
        "previous_count": previous_count,
        "new_count": max(0, len(ordered) - previous_count),
        "skipped_duplicate_count": len(ids) - len(unique_ids),
        "message_ids_seen": sorted(unique_ids),
        "latest_alert_date": max((item["date"] for item in ordered), default=None),
        "cached_total": round(sum(item["amount"] for item in ordered), 2),
        "warnings": [], "run_id": run_id,
        "matched_count": matched, "parsed_count": len(ordered),
        "rejected_count": rejected,
    }
    root.mkdir(parents=True, exist_ok=True)
    alert_tmp = metadata_tmp = None
    try:
        alert_tmp = _write_json_temp(root, "gmail_alerts.json", ordered)
        metadata_tmp = _write_json_temp(root, "sync_metadata.json", metadata)
        os.replace(alert_tmp, alerts_path)
        alert_tmp = None
        try:
            os.replace(metadata_tmp, metadata_path)
        except Exception:
            if previous_bytes is None:
                alerts_path.unlink(missing_ok=True)
            else:
                restore = _write_bytes_temp(root, "gmail_alerts.restore", previous_bytes)
                os.replace(restore, alerts_path)
            if previous_metadata_bytes is None:
                metadata_path.unlink(missing_ok=True)
            else:
                restore_metadata = _write_bytes_temp(
                    root, "sync_metadata.restore", previous_metadata_bytes)
                os.replace(restore_metadata, metadata_path)
            raise
        metadata_tmp = None
    except Exception as exc:
        raise SyncError("could not atomically write Gmail cache") from exc
    finally:
        if alert_tmp: alert_tmp.unlink(missing_ok=True)
        if metadata_tmp: metadata_tmp.unlink(missing_ok=True)
    return metadata


def run(root: Path) -> dict:
    """Authenticate and sync, leaving canonical files untouched on auth failure."""
    return sync(build_service(root), root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        result = run(args.root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except SyncError as exc:
        print(f"HSBC Gmail sync failed: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
