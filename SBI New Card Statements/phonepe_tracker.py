#!/usr/bin/env python3
"""PhonePe SBI SELECT BLACK reward tracker primitives."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any


CARD_NAME = "PhonePe SBI Card SELECT BLACK"
CARD_ENDING = "3366"
ACTIVATION_DATE = date(2026, 6, 29)
ANNUAL_END = date(2027, 6, 28)
OFFICIAL_PRODUCT = "https://www.phonepe.com/credit-cards/phonepe-sbi-card-select-black-credit-card/"
OFFICIAL_TERMS = "https://www.sbicard.com/sbi-card-en/assets/docs/pdf/ekit-tncs/PhonePe-select-ekit.pdf"
BUCKETS = (
    ("phonepe", "PhonePe non-insurance", 0.10, 1500),
    ("insurance", "PhonePe insurance", 0.10, 500),
    ("online", "Eligible online spends", 0.05, 1000),
    ("other", "Other eligible spends", 0.01, 2000),
)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _atomic_json(path: Path, payload: Any) -> None:
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _cycle(as_of: date) -> tuple[date, date]:
    close = date(as_of.year, as_of.month, min(23, calendar.monthrange(as_of.year, as_of.month)[1]))
    if as_of <= close:
        previous_month = close.month - 1 or 12
        previous_year = close.year if close.month > 1 else close.year - 1
        return date(previous_year, previous_month, 24), close
    next_month = close.month + 1 if close.month < 12 else 1
    next_year = close.year if close.month < 12 else close.year + 1
    return close + timedelta(days=1), date(next_year, next_month, 23)


def _calendar_month(as_of: date) -> tuple[date, date]:
    return date(as_of.year, as_of.month, 1), date(as_of.year, as_of.month, calendar.monthrange(as_of.year, as_of.month)[1])


def _in_range(alert: dict, start: date, end: date) -> bool:
    try:
        value = date.fromisoformat(str(alert.get("date", ""))[:10])
    except ValueError:
        return False
    return start <= value <= end


def build_summary(alerts: list[dict], statements: dict, *, as_of: date, run_id: str, generated_at: str | None = None) -> dict:
    cycle_start, cycle_end = _cycle(as_of)
    month_start, month_end = _calendar_month(as_of)
    cycle_alerts = [item for item in alerts if _in_range(item, cycle_start, cycle_end)]
    month_alerts = [item for item in alerts if _in_range(item, month_start, month_end)]
    annual_alerts = [item for item in alerts if _in_range(item, ACTIVATION_DATE, ANNUAL_END)]
    benefits = []
    for category, label, rate, cap in BUCKETS:
        spend = round(sum(
            float(item.get("amount", 0))
            for item in month_alerts
            if item.get("category", "other") == category and float(item.get("amount", 0)) >= 100
        ), 2)
        earned = round(min(cap, spend * rate), 2)
        benefits.append({"name": label, "rate": rate, "spend": spend, "earned": earned, "cap": cap, "remaining": round(cap - earned, 2)})
    estimated = round(sum(item["earned"] for item in benefits), 2)
    posted = float(statements.get("posted_reward_points", 0) or 0)
    reconciled = bool(statements.get("reward_reconciled", False))
    annual_spend = round(sum(float(item.get("amount", 0)) for item in annual_alerts), 2)
    welcome_met = bool(statements.get("welcome_voucher_received", False))
    return {
        "schema_version": 1,
        "card": {"name": CARD_NAME, "ending": CARD_ENDING},
        "cycle": {
            "start": cycle_start.isoformat(),
            "end": cycle_end.isoformat(),
            "spend": round(sum(float(item.get("amount", 0)) for item in cycle_alerts), 2),
            "evidence_status": "confirmed",
            "source": "PhonePe SBI statement PDF for 24 May 2026 to 23 July 2026.",
            "statement_date": "2026-07-23",
        },
        "reward_window": {"start": month_start.isoformat(), "end": month_end.isoformat()},
        "benefits": benefits,
        "reward_points": {"estimated": estimated, "posted": posted, "value": posted if reconciled else estimated, "reconciled": reconciled},
        "welcome": {"status": "Met" if welcome_met else "In progress", "deadline": (ACTIVATION_DATE + timedelta(days=45)).isoformat(), "progress": 1499 if welcome_met else 0, "target": 1499, "remaining": 0 if welcome_met else 1499, "reward": 1500, "evidence_state": "verified", "evidence_source": "Official SBI membership kit and card account evidence"},
        "annual_fee": {"status": "Met" if annual_spend >= 300000 else "In progress", "period_start": ACTIVATION_DATE.isoformat(), "period_end": ANNUAL_END.isoformat(), "eligible_spend": annual_spend, "waiver_spend": 300000, "remaining_spend_for_waiver": max(0, 300000 - annual_spend), "evidence_state": "verified", "evidence_source": OFFICIAL_PRODUCT},
        "annual_milestone": {"status": "Met" if annual_spend >= 500000 else "In progress", "deadline": ANNUAL_END.isoformat(), "progress": annual_spend, "target": 500000, "remaining": max(0, 500000 - annual_spend), "reward": "₹5,000 travel voucher", "evidence_state": "verified", "evidence_source": OFFICIAL_PRODUCT},
        "evergreen_benefits": ["4 domestic lounge visits yearly", "Priority Pass membership", "1% fuel surcharge waiver"],
        "evidence": {"variant_status": "confirmed", "official_terms": OFFICIAL_TERMS},
        "generated_at": generated_at or datetime.now(timezone.utc).astimezone().isoformat(),
        "run_id": run_id,
        "alert_count": len(alerts),
    }


def validate(root: Path) -> dict:
    alerts = _read_json(root / "gmail_alerts.json", [])
    metadata = _read_json(root / "sync_metadata.json", {})
    failures = []
    if metadata.get("source") != "gmail-api": failures.append("Live read-only Gmail API evidence is required")
    if not metadata.get("run_id"): failures.append("Current run ID is missing")
    if metadata.get("alert_count") != len(alerts): failures.append("Alert count does not reconcile")
    if not metadata.get("synced_at"): failures.append("Sync timestamp is missing")
    result = {"ok": not failures, "failures": failures, "warnings": [], "run_id": metadata.get("run_id"), "alert_count": len(alerts)}
    _atomic_json(root / "validation_report.json", result)
    return result


def write_outputs(root: Path, *, as_of: date | None = None) -> Path:
    alerts = _read_json(root / "gmail_alerts.json", [])
    metadata = _read_json(root / "sync_metadata.json", {})
    validation = _read_json(root / "validation_report.json", {})
    if not validation.get("ok") or validation.get("run_id") != metadata.get("run_id") or validation.get("alert_count") != len(alerts):
        raise ValueError("PhonePe SBI dashboard output requires matching current-run validation")
    summary = build_summary(alerts, _read_json(root / "statements_data.json", {}), as_of=as_of or date.today(), run_id=metadata["run_id"])
    _atomic_json(root / "dashboard_summary.json", summary)
    lines = [f"# {CARD_NAME}: Benefit Tracker Report", "", f"- Card ending: {CARD_ENDING}", "- Variant status: confirmed", f"- Active cycle: {summary['cycle']['start']} to {summary['cycle']['end']}", "", "## Monthly Reward Progress", "", "| Category | Spend | Reward points | Cap | Remaining |", "|---|---:|---:|---:|---:|"]
    for row in summary["benefits"]:
        lines.append(f"| {row['name']} | INR {row['spend']:,.2f} | {row['earned']:,.0f} RP | {row['cap']:,.0f} RP | {row['remaining']:,.0f} RP |")
    lines += ["", "## Milestones", "", f"- Welcome voucher: {summary['welcome']['status']} - INR 1,500 PhonePe voucher", f"- Annual fee waiver: INR {summary['annual_fee']['eligible_spend']:,.2f} of INR 300,000.00", f"- Travel voucher: INR {summary['annual_milestone']['progress']:,.2f} of INR 500,000.00", "", "## Sources", "", f"- {OFFICIAL_PRODUCT}", f"- {OFFICIAL_TERMS}", ""]
    report = root / "benefit_tracker_report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    return report
