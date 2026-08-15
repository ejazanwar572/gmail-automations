#!/usr/bin/env python3
"""Freshness and reconciliation checks shared by card trackers."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

METADATA_FILE = "sync_metadata.json"
DEFAULT_MAX_AGE_HOURS = 36
MONEY_RE = re.compile(r"(?:INR|Rs\.?|₹)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.IGNORECASE)
DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_amount(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    match = MONEY_RE.search(str(value).replace(",", ""))
    return float(match.group(1)) if match else 0.0


def parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def load_alerts(card_dir: Path | str) -> list[dict[str, Any]]:
    payload = load_json(Path(card_dir) / "gmail_alerts.json", [])
    if isinstance(payload, dict):
        payload = payload.get("alerts", [])
    return payload if isinstance(payload, list) else []


def alert_identity(alert: dict[str, Any]) -> tuple[Any, ...]:
    message_id = str(alert.get("message_id") or "").strip()
    if message_id:
        return "message_id", message_id
    parsed = parse_date(alert.get("date") or alert.get("Date"))
    date_key = parsed.date().isoformat() if parsed else str(alert.get("date") or alert.get("Date") or "")
    amount_cents = int(round(parse_amount(alert.get("amount") or alert.get("Amount")) * 100))
    merchant = str(alert.get("merchant") or alert.get("payee") or alert.get("subject") or "").strip().upper()
    merchant = re.sub(r"\s+", " ", merchant)
    return "business_fields", date_key, amount_cents, merchant


def unique_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    unique = []
    for alert in alerts:
        key = alert_identity(alert)
        if key in seen:
            continue
        seen.add(key)
        unique.append(alert)
    return unique


def alert_total(alerts: list[dict[str, Any]]) -> float:
    return round(sum(parse_amount(a.get("amount") or a.get("Amount")) for a in unique_alerts(alerts)), 2)


def latest_alert_date(alerts: list[dict[str, Any]]) -> str | None:
    dates = [d for d in (parse_date(a.get("date") or a.get("Date")) for a in alerts) if d]
    return max(dates).date().isoformat() if dates else None


def env_expected_total(prefix: str | None = None) -> float | None:
    names = []
    if prefix:
        names.append(f"{prefix}_APP_TOTAL")
    names.extend(["CARD_APP_TOTAL", "RECONCILE_EXPECTED_TOTAL"])
    for name in names:
        value = os.environ.get(name)
        if value:
            return parse_amount(value)
    return None


def write_sync_metadata(
    card_dir: Path | str,
    *,
    card_name: str = "",
    card_ending: str = "",
    source: str,
    query: str = "",
    alerts: list[dict[str, Any]] | None = None,
    previous_count: int | None = None,
    new_count: int = 0,
    skipped_duplicate_count: int = 0,
    message_ids: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    card_dir = Path(card_dir)
    alerts = alerts if alerts is not None else load_alerts(card_dir)
    unique = unique_alerts(alerts)
    payload = {
        "synced_at": utc_now_iso(),
        "source": source,
        "query": query,
        "card_name": card_name,
        "card_ending": card_ending,
        "alert_count": len(alerts),
        "unique_alert_count": len(unique),
        "previous_count": previous_count,
        "new_count": new_count,
        "skipped_duplicate_count": skipped_duplicate_count,
        "message_ids_seen": message_ids or [],
        "latest_alert_date": latest_alert_date(unique),
        "cached_total": alert_total(unique),
        "warnings": warnings or [],
    }
    write_json(card_dir / METADATA_FILE, payload)
    return payload


def load_sync_metadata(card_dir: Path | str) -> dict[str, Any]:
    return load_json(Path(card_dir) / METADATA_FILE, {})


def validate_freshness(
    card_dir: Path | str,
    *,
    card_name: str = "card",
    expected_total: float | None = None,
    env_prefix: str | None = None,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
    require_metadata: bool = True,
    require_connector_evidence: bool = False,
) -> dict[str, Any]:
    card_dir = Path(card_dir)
    alerts = load_alerts(card_dir)
    metadata = load_sync_metadata(card_dir)
    warnings: list[str] = []
    failures: list[str] = []

    if not metadata:
        message = f"{METADATA_FILE} is missing; run the Gmail sync before trusting {card_name} totals."
        (failures if require_metadata else warnings).append(message)
    else:
        synced_at = parse_date(metadata.get("synced_at"))
        if synced_at:
            age_hours = (datetime.now(timezone.utc) - synced_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                failures.append(f"Gmail sync is stale: last sync was {age_hours:.1f} hours ago; rerun sync before trusting {card_name} totals.")
        else:
            failures.append(f"{METADATA_FILE} has no parseable synced_at timestamp.")

        metadata_count = metadata.get("unique_alert_count")
        actual_count = len(unique_alerts(alerts))
        if metadata_count is not None and int(metadata_count) != actual_count:
            failures.append(f"Cached alert count changed after sync metadata was written: metadata={metadata_count}, current={actual_count}.")

        if require_connector_evidence and not metadata.get("message_ids_seen"):
            warnings.append("No Gmail message IDs were recorded for this sync; live Gmail coverage cannot be independently proven from metadata.")
        if metadata.get("source") in {"cached-alerts", "report-rebuild"}:
            failures.append(f"Sync source is {metadata.get('source')}; this is not a fresh Gmail refresh.")

    expected = expected_total if expected_total is not None else env_expected_total(env_prefix)
    actual_total = alert_total(alerts)
    if expected is not None:
        delta = round(actual_total - expected, 2)
        if abs(delta) > 1.0:
            failures.append(f"Tracker total {actual_total:.2f} does not reconcile to expected/app total {expected:.2f}; delta {delta:.2f}.")

    return {
        "ok": not failures,
        "warnings": warnings,
        "failures": failures,
        "cached_total": actual_total,
        "expected_total": expected,
        "metadata": metadata,
    }


def freshness_summary(card_dir: Path | str) -> str:
    metadata = load_sync_metadata(card_dir)
    if not metadata:
        return "Stale cache: sync metadata missing."
    source = metadata.get("source", "unknown")
    synced_at = metadata.get("synced_at", "unknown time")
    total = metadata.get("cached_total")
    count = metadata.get("unique_alert_count", metadata.get("alert_count", "unknown"))
    total_text = f"INR {float(total):,.2f}" if isinstance(total, (int, float)) else "unknown total"
    return f"Verified from {source} at {synced_at}; {count} unique alerts; cached total {total_text}."
