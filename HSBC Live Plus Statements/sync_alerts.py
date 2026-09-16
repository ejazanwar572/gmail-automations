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
TRANSACTION_SUBJECT_NEW = "Credit Card Transaction Alert"
TRANSACTION_SUBJECTS = {TRANSACTION_SUBJECT, TRANSACTION_SUBJECT_NEW}
QUERY = f'(subject:"{TRANSACTION_SUBJECT_NEW}" OR subject:"{TRANSACTION_SUBJECT}") -in:spam -in:trash'
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
    """Load local authorized-user JSON, Streamlit Cloud secrets, or translate Gmail MCP credential JSON."""
    local = root / "token.json"
    if local.exists():
        return credentials_class.from_authorized_user_file(str(local), SCOPES)

    # Check Streamlit Cloud secrets or environment variables
    secrets_data = None
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "gmail_credentials" in st.secrets:
                raw = st.secrets["gmail_credentials"]
                secrets_data = dict(raw) if hasattr(raw, "items") else json.loads(str(raw))
            elif "GMAIL_CREDENTIALS" in st.secrets:
                raw = st.secrets["GMAIL_CREDENTIALS"]
                secrets_data = dict(raw) if hasattr(raw, "items") else json.loads(str(raw))
    except Exception:
        secrets_data = None

    if not secrets_data and "GMAIL_CREDENTIALS" in os.environ:
        try:
            secrets_data = json.loads(os.environ["GMAIL_CREDENTIALS"])
        except Exception:
            pass

    if secrets_data:
        try:
            if hasattr(credentials_class, "from_authorized_user_info"):
                return credentials_class.from_authorized_user_info(secrets_data, SCOPES)
            token = secrets_data.get("token") or secrets_data.get("access_token")
            return credentials_class(
                token=token,
                refresh_token=secrets_data.get("refresh_token"),
                token_uri=secrets_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=secrets_data.get("client_id"),
                client_secret=secrets_data.get("client_secret"),
                scopes=SCOPES,
            )
        except Exception as exc:
            raise SyncError(f"Failed to load Gmail credentials from secrets: {exc}") from exc

    if not shared_token.exists() or not shared_keys.exists():
        raise SyncError("shared Gmail token or OAuth keys not found (set [gmail_credentials] in Streamlit Cloud secrets)")
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
