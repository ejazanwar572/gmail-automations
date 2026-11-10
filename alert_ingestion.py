#!/usr/bin/env python3
"""
Deep Alert Ingestion Module.
Provides shared ports & adapters, OAuth resolution, MIME decoding,
message pagination, and transactional atomic cache writes across cards.
"""

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
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple
import uuid


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SHARED_TOKEN = Path("/Users/ejazanwar/.gmail-mcp/credentials.json")
SHARED_KEYS = Path("/Users/ejazanwar/.gmail-mcp/gcp-oauth.keys.json")


class SyncError(RuntimeError):
    """The Gmail sync could not safely produce a complete cache."""


# ---------------------------------------------------------------------------
# MIME & Header Decoding Utilities
# ---------------------------------------------------------------------------

def decode_base64_urlsafe(data: str) -> str:
    """Decode base64url data with missing padding restoration."""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def iter_mime_parts(payload: dict, mime: str):
    """Recursively yield decoded text from payload parts matching mime type."""
    if payload.get("mimeType", "").lower() == mime:
        data = payload.get("body", {}).get("data")
        if data:
            yield decode_base64_urlsafe(data)
    for part in payload.get("parts", []):
        yield from iter_mime_parts(part, mime)


def decode_message_body(payload: dict) -> str:
    """Recursively select plain text, falling back to clean readable HTML."""
    plain = list(iter_mime_parts(payload, "text/plain"))
    if plain:
        return "\n".join(plain)
    html = list(iter_mime_parts(payload, "text/html"))
    if not html:
        return ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", "\n".join(html))
    text = re.sub(r"<[^>]+>", " ", text)
    return unescape(re.sub(r"[ \t]+", " ", text))


def get_header(message: dict, name: str) -> str:
    """Case-insensitive search for a header value in message payload."""
    for item in message.get("payload", {}).get("headers", []):
        if item.get("name", "").lower() == name.lower():
            return item.get("value", "")
    return ""


def get_email_date(message: dict) -> str:
    """Parse email Date header into ISO format; fallback to internalDate."""
    raw = get_header(message, "Date")
    if raw:
        try:
            return parsedate_to_datetime(raw).isoformat()
        except (TypeError, ValueError):
            pass
    return datetime.fromtimestamp(
        int(message.get("internalDate", 0)) / 1000, timezone.utc
    ).isoformat()


# ---------------------------------------------------------------------------
# OAuth Credentials & Gmail Service Seam
# ---------------------------------------------------------------------------

def load_credentials(
    root: Path,
    credentials_class: Any,
    shared_token: Path = SHARED_TOKEN,
    shared_keys: Path = SHARED_KEYS,
    scopes: Optional[List[str]] = None,
):
    """Load authorized user credentials from local dir, Streamlit secrets, or shared MCP keys."""
    scopes = scopes or SCOPES
    local = root / "token.json"
    if local.exists():
        return credentials_class.from_authorized_user_file(str(local), scopes)

    secrets_data = None
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GMAIL_CREDENTIALS" in st.secrets:
            val = st.secrets["GMAIL_CREDENTIALS"]
            if isinstance(val, str):
                secrets_data = json.loads(val)
            elif hasattr(val, "get"):
                secrets_data = dict(val)
    except Exception:
        pass

    if not secrets_data and "GMAIL_CREDENTIALS" in os.environ:
        try:
            val = os.environ["GMAIL_CREDENTIALS"]
            if isinstance(val, str):
                secrets_data = json.loads(val)
            elif hasattr(val, "get"):
                secrets_data = dict(val)
        except Exception:
            pass

    if secrets_data:
        try:
            expiry = None
            if "expiry" in secrets_data:
                try:
                    expiry = datetime.fromisoformat(secrets_data["expiry"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    expiry = None
            return credentials_class(
                token=secrets_data.get("token"),
                refresh_token=secrets_data.get("refresh_token"),
                token_uri=secrets_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=secrets_data.get("client_id"),
                client_secret=secrets_data.get("client_secret"),
                scopes=scopes,
                expiry=expiry,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SyncError("Streamlit / env Gmail credential schema is invalid") from exc

    if not shared_token.exists() or not shared_keys.exists():
        raise SyncError("Gmail credentials are not configured locally or in shared MCP store")

    try:
        token_data = json.loads(shared_token.read_text())
        keys_data = json.loads(shared_keys.read_text())
        key_data = keys_data.get("installed") or keys_data.get("web") or keys_data
        
        token_scopes = token_data.get("scope") or scopes
        if isinstance(token_scopes, str):
            token_scopes = token_scopes.split()

        expiry = None
        if "expiry_date" in token_data and token_data["expiry_date"] is not None:
            try:
                expiry = datetime.fromtimestamp(
                    float(token_data["expiry_date"]) / 1000, timezone.utc
                ).replace(tzinfo=None)
            except (ValueError, TypeError):
                expiry = None
        elif "expiry" in token_data and token_data["expiry"] is not None:
            try:
                expiry = datetime.fromisoformat(str(token_data["expiry"]).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                expiry = None

        token_val = token_data.get("access_token") or token_data.get("token")
        return credentials_class(
            token=token_val,
            refresh_token=token_data.get("refresh_token"),
            token_uri=key_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=key_data["client_id"],
            client_secret=key_data["client_secret"],
            scopes=token_scopes,
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


# ---------------------------------------------------------------------------
# Transactional Atomic Cache Writes & Rollback
# ---------------------------------------------------------------------------

def write_temp_file(root: Path, target: str, value: Any, *, binary: bool = False) -> Path:
    """Safely write temp file with fsync."""
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


def rewrite_exact_bytes(path: Path, previous: bytes) -> None:
    """Rewrite exact previous bytes with fsync."""
    with path.open("wb") as handle:
        handle.write(previous)
        handle.flush()
        os.fsync(handle.fileno())


def restore_file_transaction(root: Path, path: Path, previous: Optional[bytes]) -> None:
    """Restore previous file state or unlink if no prior state existed."""
    if previous is None:
        path.unlink(missing_ok=True)
        return
    restore_tmp = None
    try:
        restore_tmp = write_temp_file(root, f"{path.name}.restore", previous, binary=True)
        try:
            os.replace(restore_tmp, path)
            restore_tmp = None
        except Exception:
            rewrite_exact_bytes(path, previous)
    finally:
        if restore_tmp:
            restore_tmp.unlink(missing_ok=True)


def atomic_write_cache(
    root: Path,
    alerts_data: List[dict],
    metadata_data: dict,
    redemptions_data: Optional[List[dict]] = None,
) -> None:
    """
    Two-phase atomic write of alerts and metadata files.
    Restores exact prior bytes if replacement fails at any point.
    """
    root.mkdir(parents=True, exist_ok=True)
    alerts_path = root / "gmail_alerts.json"
    metadata_path = root / "sync_metadata.json"
    redemptions_path = root / "redemptions_cache.json"

    old_alerts = alerts_path.read_bytes() if alerts_path.exists() else None
    old_metadata = metadata_path.read_bytes() if metadata_path.exists() else None
    old_redemptions = redemptions_path.read_bytes() if redemptions_path.exists() else None

    alert_tmp = None
    metadata_tmp = None
    redemptions_tmp = None

    try:
        alert_tmp = write_temp_file(root, "gmail_alerts.json", alerts_data)
        metadata_tmp = write_temp_file(root, "sync_metadata.json", metadata_data)
        if redemptions_data is not None:
            redemptions_tmp = write_temp_file(root, "redemptions_cache.json", redemptions_data)

        # 1. Replace alerts_path first
        os.replace(alert_tmp, alerts_path)
        alert_tmp = None

        # 2. Replace metadata_path second
        try:
            os.replace(metadata_tmp, metadata_path)
        except Exception as write_exc:
            restore_errors = []
            for path, previous in ((alerts_path, old_alerts), (metadata_path, old_metadata)):
                try:
                    restore_file_transaction(root, path, previous)
                except Exception as restore_exc:
                    restore_errors.append(restore_exc)
            if restore_errors:
                raise SyncError(
                    "prior Gmail cache preservation/recovery failed after atomic write error"
                ) from restore_errors[0]
            raise write_exc
        metadata_tmp = None

        # 3. Optional redemptions cache
        if redemptions_tmp:
            try:
                os.replace(redemptions_tmp, redemptions_path)
                redemptions_tmp = None
            except Exception:
                pass

    except SyncError:
        raise
    except Exception as exc:
        raise SyncError("could not atomically write Gmail cache") from exc
    finally:
        if alert_tmp:
            alert_tmp.unlink(missing_ok=True)
        if metadata_tmp:
            metadata_tmp.unlink(missing_ok=True)
        if redemptions_tmp:
            redemptions_tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Ports & Adapters: Alert Source Seam
# ---------------------------------------------------------------------------

class AlertSourceAdapter(Protocol):
    """Seam defining message retrieval from external email provider or test fixtures."""

    def fetch_messages_for_query(self, query: str) -> Tuple[List[str], List[dict]]:
        """Return (all_message_ids_seen_in_order, list_of_full_message_payloads)."""
        ...


class GmailApiAdapter:
    """Production adapter using Gmail API client or duck-typed fake service."""

    def __init__(self, service: Any):
        self.service = service

    def fetch_messages_for_query(self, query: str) -> Tuple[List[str], List[dict]]:
        try:
            api = self.service.users().messages()
            ids: List[str] = []
            token = None
            while True:
                kwargs = {"userId": "me", "q": query}
                if token:
                    kwargs["pageToken"] = token
                page = api.list(**kwargs).execute()
                ids.extend(item["id"] for item in page.get("messages", []))
                token = page.get("nextPageToken")
                if not token:
                    break
            unique_ids = list(dict.fromkeys(ids))
            messages = [
                api.get(userId="me", id=mid, format="full").execute()
                for mid in unique_ids
            ]
            return ids, messages
        except Exception as exc:
            raise SyncError("Gmail API retrieval failed") from exc


class FixtureAlertAdapter:
    """Test adapter reading directly from pre-loaded message dicts."""

    def __init__(self, messages: List[dict]):
        self.messages = messages

    def fetch_messages_for_query(self, query: str) -> Tuple[List[str], List[dict]]:
        ids = [m["id"] for m in self.messages]
        return ids, list(self.messages)
