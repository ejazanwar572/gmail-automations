#!/usr/bin/env python3
"""Read HDFC Diners Black Metal purchase alerts from Gmail."""

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
TRANSACTION_SUBJECT = "A payment was made using your Credit Card"
QUERY = f'from:alerts@hdfcbank.bank.in subject:"{TRANSACTION_SUBJECT}" "ending 2360" -in:trash -in:spam'
CARD_NAME = "HDFC Diners Black Metal Credit Card"
CARD_ENDING = "2360"
SHARED_TOKEN = Path("/Users/ejazanwar/.gmail-mcp/credentials.json")
SHARED_KEYS = Path("/Users/ejazanwar/.gmail-mcp/gcp-oauth.keys.json")


class SyncError(RuntimeError):
    """The Gmail sync could not safely produce a complete cache."""


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
        "utf-8", errors="replace")


def _parts(payload: dict, mime: str):
    if payload.get("mimeType", "").lower() == mime:
        data = payload.get("body", {}).get("data")
        if data:
            yield _decode(data)
    for part in payload.get("parts", []):
        yield from _parts(part, mime)


def decode_message_body(payload: dict) -> str:
    plain = list(_parts(payload, "text/plain"))
    if plain:
        return "\n".join(plain)
    html = list(_parts(payload, "text/html"))
    if not html:
        return ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", "\n".join(html))
    return unescape(re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", " ", text)))


def is_transaction_subject(subject: str) -> bool:
    normalized = " ".join(subject.split()).lower()
    return (normalized == TRANSACTION_SUBJECT.lower() or "transaction" in normalized) and not any(
        word in normalized for word in ("statement", "otp", "declined", "failed", "refund"))


def is_hard_filtered_candidate(text: str) -> bool:
    normalized = " ".join(text.split())
    if re.search(r"\b(?:declined|refund(?:ed)?|statement)\b", normalized, re.IGNORECASE):
        return False
    return bool(
        re.search(r"(?:spent|purchase|transaction|has been debited)", normalized, re.IGNORECASE)
        and re.search(r"(?:ending|end(?:ing)? in|xx)\s*2360\b", normalized, re.IGNORECASE)
    )


def parse_transaction(text: str) -> dict[str, str | float]:
    normalized = " ".join(text.split())
    if not is_hard_filtered_candidate(normalized):
        raise SyncError("message is not an HDFC card 2360 purchase alert")
    match = re.search(
        r"(?:Rs\.?|INR)\s*(?P<amount>\d[\d,]*(?:\.\d{1,2})?)\s+"
        r"(?:was\s+)?(?:spent|debited|used).*?(?:at|to)\s+"
        r"(?P<merchant>.+?)\s+on\s+"
        r"(?P<date>\d{1,2}[-/][A-Za-z0-9]{1,3}[-/]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4})(?:[.,]|\s+at\b|$)",
        normalized, re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"(?:Rs\.?|INR)\s*(?P<amount>\d[\d,]*(?:\.\d{1,2})?)\s+"
            r"has been debited from your HDFC Bank Credit Card ending 2360\s+"
            r"towards\s+(?P<merchant>.+?)\s+on\s+"
            r"(?P<date>\d{1,2}\s+[A-Za-z]{3},\s+\d{4})\s+at\b",
            normalized, re.IGNORECASE,
        )
    if not match:
        raise SyncError("hard-filtered HDFC transaction alert could not be parsed")
    raw_date = match.group("date")
    parsed_date = None
    for pattern in ("%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d/%b/%Y",
                    "%d %b %Y", "%d %b, %Y"):
        try:
            parsed_date = datetime.strptime(raw_date, pattern).date().isoformat()
            break
        except ValueError:
            continue
    if parsed_date is None:
        raise SyncError("HDFC transaction date could not be parsed")
    return {
        "date": parsed_date,
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
    return datetime.fromtimestamp(
        int(message.get("internalDate", 0)) / 1000, timezone.utc).isoformat()


def load_credentials(root: Path, credentials_class,
                     shared_token: Path = SHARED_TOKEN, shared_keys: Path = SHARED_KEYS):
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
        expiry = (datetime.fromtimestamp(float(expiry_millis) / 1000, timezone.utc)
                  .replace(tzinfo=None) if expiry_millis is not None else None)
        return credentials_class(
            token=token_data["access_token"], refresh_token=token_data["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token", client_id=key_data["client_id"],
            client_secret=key_data["client_secret"], scopes=scopes, expiry=expiry)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SyncError("shared Gmail credential schema is invalid") from exc


def build_service(root: Path):
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


def _write_temp(root: Path, target: str, value, *, binary=False) -> Path:
    fd, name = tempfile.mkstemp(prefix=f".{target}.", suffix=".tmp", dir=root)
    path = Path(name)
    try:
        with os.fdopen(fd, "wb" if binary else "w") as handle:
            if binary:
                handle.write(value)
            else:
                json.dump(value, handle, indent=2, sort_keys=True)
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _rewrite_exact(path: Path, previous: bytes) -> None:
    with path.open("wb") as handle:
        handle.write(previous)
        handle.flush()
        os.fsync(handle.fileno())


def _restore_file(root: Path, path: Path, previous: bytes | None) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
        return
    restore_tmp = None
    try:
        restore_tmp = _write_temp(root, f"{path.name}.restore", previous, binary=True)
        try:
            os.replace(restore_tmp, path)
            restore_tmp = None
        except Exception:
            _rewrite_exact(path, previous)
    finally:
        if restore_tmp:
            restore_tmp.unlink(missing_ok=True)


def sync(service, root: Path, run_id: str | None = None,
         *, authoritative_empty: bool = False) -> dict:
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

    alerts = {}
    for message in messages:
        subject = _header(message, "Subject")
        body = decode_message_body(message.get("payload", {}))
        parsed = parse_transaction(body)
        message_id = message["id"]
        alerts[message_id] = {
            **parsed, "subject": subject, "message_id": message_id,
            "email_date": _email_date(message), "source": "gmail-api",
        }
    ordered = sorted(alerts.values(), key=lambda item: (item["date"], item["message_id"]))
    alerts_path, metadata_path = root / "gmail_alerts.json", root / "sync_metadata.json"
    old_alerts = alerts_path.read_bytes() if alerts_path.exists() else None
    old_metadata = metadata_path.read_bytes() if metadata_path.exists() else None
    if not ordered and not authoritative_empty and old_alerts is not None:
        try:
            prior = json.loads(old_alerts)
        except (json.JSONDecodeError, TypeError):
            prior = None
        if isinstance(prior, list) and prior:
            raise SyncError("empty Gmail result is not authoritative; preserved prior cache")
    emitted_ids = sorted(alerts)
    metadata = {
        "source": "gmail-api", "query": QUERY, "card_name": CARD_NAME,
        "card_ending": CARD_ENDING, "run_id": run_id,
        "alert_count": len(ordered), "unique_alert_count": len(ordered),
        "parsed_count": len(ordered), "message_ids_seen": emitted_ids,
        "queried_message_ids": sorted(unique_ids),
        "latest_alert_date": max((item["date"] for item in ordered), default=None),
        "cached_total": round(sum(item["amount"] for item in ordered), 2),
        "skipped_duplicate_count": len(ids) - len(unique_ids),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
    root.mkdir(parents=True, exist_ok=True)
    alert_tmp = metadata_tmp = None
    try:
        alert_tmp = _write_temp(root, "gmail_alerts.json", ordered)
        metadata_tmp = _write_temp(root, "sync_metadata.json", metadata)
        os.replace(alert_tmp, alerts_path); alert_tmp = None
        try:
            os.replace(metadata_tmp, metadata_path)
        except Exception as write_exc:
            restore_errors = []
            for path, previous in ((alerts_path, old_alerts), (metadata_path, old_metadata)):
                try:
                    _restore_file(root, path, previous)
                except Exception as restore_exc:
                    restore_errors.append(restore_exc)
            if restore_errors:
                raise SyncError(
                    "prior Gmail cache preservation/recovery failed after atomic write error"
                ) from restore_errors[0]
            raise write_exc
        metadata_tmp = None
    except SyncError:
        raise
    except Exception as exc:
        raise SyncError("could not atomically write Gmail cache") from exc
    finally:
        if alert_tmp: alert_tmp.unlink(missing_ok=True)
        if metadata_tmp: metadata_tmp.unlink(missing_ok=True)
    return metadata


def run(root: Path) -> dict:
    return sync(build_service(root), root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.root), indent=2, sort_keys=True))
        return 0
    except SyncError as exc:
        print(f"HDFC Gmail sync failed: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
