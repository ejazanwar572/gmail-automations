#!/usr/bin/env python3
"""Read HSBC transaction alerts from Gmail without interactive authentication."""

from __future__ import annotations

import argparse
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
TRANSACTION_SUBJECT = "You have used your HSBC Credit Card ending with 8690 for a purchase transaction"
QUERY = f'subject:"{TRANSACTION_SUBJECT}" -in:spam -in:trash'
SHARED_TOKEN = Path("/Users/ejazanwar/.gmail-mcp/credentials.json")
SHARED_KEYS = Path("/Users/ejazanwar/.gmail-mcp/gcp-oauth.keys.json")


class SyncError(RuntimeError):
    """The Gmail sync could not safely produce a complete cache."""


def _decode(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _parts(payload: dict, mime: str):
    if payload.get("mimeType", "").lower() == mime:
        data = payload.get("body", {}).get("data")
        if data:
            yield _decode(data)
    for part in payload.get("parts", []):
        yield from _parts(part, mime)


def decode_message_body(payload: dict) -> str:
    """Recursively select plain text, falling back to readable HTML."""
    plain = list(_parts(payload, "text/plain"))
    if plain:
        return "\n".join(plain)
    html = list(_parts(payload, "text/html"))
    if not html:
        return ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", "\n".join(html))
    text = re.sub(r"<[^>]+>", " ", text)
    return unescape(re.sub(r"[ \t]+", " ", text))


def is_hard_filtered_candidate(text: str) -> bool:
    normalized = " ".join(text.split())
    return bool(re.search(
        r"Credit card no ending with 8690\s*,?\s*has been used for INR\s+",
        normalized, re.IGNORECASE,
    ))


def is_transaction_subject(subject: str) -> bool:
    """Identify only the exact HSBC purchase-alert subject for card 8690."""
    return subject.strip() == TRANSACTION_SUBJECT


def parse_transaction(text: str) -> dict[str, str | float]:
    normalized = " ".join(text.split())
    match = re.search(
        r"Credit card no ending with 8690\s*,?\s*has been used for INR\s+"
        r"(?P<amount>\d[\d,]*\.\d{2})\s+for payment to\s+"
        r"(?P<merchant>.+?)\s+on\s+(?P<date>\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+at\s+\d{1,2}:\d{2}",
        normalized, re.IGNORECASE,
    )
    if not match:
        raise SyncError("hard-filtered HSBC transaction alert could not be parsed")
    try:
        date = datetime.strptime(match.group("date"), "%d %b %Y").date().isoformat()
    except ValueError as exc:
        raise SyncError("HSBC transaction date could not be parsed") from exc
    return {
        "date": date,
        "merchant": match.group("merchant").strip(),
        "amount": float(match.group("amount").replace(",", "")),
    }


def _header(message: dict, name: str) -> str:
    for item in message.get("payload", {}).get("headers", []):
        if item.get("name", "").lower() == name.lower():
            return item.get("value", "")
    return ""


def _email_date(message: dict) -> str:
    raw = _header(message, "Date")
    if raw:
        try:
            return parsedate_to_datetime(raw).isoformat()
        except (TypeError, ValueError):
            pass
    millis = int(message.get("internalDate", 0))
    return datetime.fromtimestamp(millis / 1000, timezone.utc).isoformat()


def credential_paths(root: Path, shared_token: Path = SHARED_TOKEN,
                     shared_keys: Path = SHARED_KEYS) -> tuple[Path, Path]:
    local = root / "token.json"
    return (local if local.exists() else shared_token, shared_keys)


def load_credentials(root: Path, credentials_class,
                     shared_token: Path = SHARED_TOKEN,
                     shared_keys: Path = SHARED_KEYS):
    """Load local authorized-user JSON or translate Gmail MCP credential JSON."""
    local = root / "token.json"
    if local.exists():
        return credentials_class.from_authorized_user_file(str(local), SCOPES)
    if not shared_token.exists() or not shared_keys.exists():
        raise SyncError("shared Gmail token or OAuth keys not found")
    try:
        token_data = json.loads(shared_token.read_text())
        key_data = json.loads(shared_keys.read_text())["installed"]
        scopes = token_data.get("scope") or SCOPES
        if isinstance(scopes, str):
            scopes = scopes.split()
        expiry_millis = token_data.get("expiry_date")
        expiry = (datetime.fromtimestamp(float(expiry_millis) / 1000, timezone.utc).replace(tzinfo=None)
                  if expiry_millis is not None else None)
        return credentials_class(
            token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=key_data["client_id"],
            client_secret=key_data["client_secret"],
            scopes=scopes,
            expiry=expiry,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SyncError("shared Gmail credential schema is invalid") from exc


def build_service(root: Path):
    """Build a readonly Gmail client from existing credentials only."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise SyncError("Google Gmail API dependencies are unavailable") from exc
    try:
        credentials = load_credentials(root, Credentials)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials.valid:
            raise SyncError("existing Gmail credentials are invalid and cannot refresh")
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)
    except SyncError:
        raise
    except Exception as exc:
        raise SyncError("Gmail authentication failed") from exc


def _write_json_temp(root: Path, target: str, value) -> Path:
    fd, name = tempfile.mkstemp(prefix=f".{target}.", suffix=".tmp", dir=root)
    path = Path(name)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _write_bytes_temp(root: Path, target: str, value: bytes) -> Path:
    fd, name = tempfile.mkstemp(prefix=f".{target}.", suffix=".tmp", dir=root)
    path = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def sync(service, root: Path, *, run_id: str | None = None) -> dict:
    run_id = run_id or str(uuid.uuid4())
    try:
        api = service.users().messages()
        ids, token = [], None
        while True:
            page = api.list(userId="me", q=QUERY, pageToken=token).execute()
            ids.extend(item["id"] for item in page.get("messages", []))
            token = page.get("nextPageToken")
            if not token:
                break
        unique_ids = list(dict.fromkeys(ids))
        messages = [api.get(userId="me", id=mid, format="full").execute()
                    for mid in unique_ids]
    except Exception as exc:
        raise SyncError("Gmail API retrieval failed") from exc

    alerts, rejected, matched = {}, 0, 0
    for message in messages:
        subject = _header(message, "Subject")
        if not is_transaction_subject(subject):
            rejected += 1
            continue
        body = decode_message_body(message.get("payload", {}))
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
        "card_name": "HSBC Live+ Credit Card", "card_ending": "8690",
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = run(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
