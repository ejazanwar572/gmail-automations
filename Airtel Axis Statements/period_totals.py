"""Structured lifetime/current-cycle totals for the Airtel Axis dashboard."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
import hashlib
import re

from transaction_classifier import classify_transactions


EXCLUDED_DEBIT_TERMS = (
    "GST", "JOINING FEE", "ANNUAL FEE", "RENEWAL FEE", "INTEREST",
    "EMI PRINCIPAL", "EMI PROCESSING", "TRANSACTION CONVERSION",
    "PAYMENT RECEIVED", "CASHBACK CREDIT", "LATE PAYMENT", "OVERLIMIT",
)
EXCLUDED_CREDIT_TERMS = ("PAYMENT RECEIVED", "CASHBACK CREDIT", "TRANSACTION CONVERSION")


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%d/%m/%Y").date()


def cycle_bounds(day: date) -> tuple[date, date]:
    if day.day >= 13:
        start = day.replace(day=13)
        if day.month == 12:
            end = date(day.year + 1, 1, 12)
        else:
            end = date(day.year, day.month + 1, 12)
    else:
        end = day.replace(day=12)
        if day.month == 1:
            start = date(day.year - 1, 12, 13)
        else:
            start = date(day.year, day.month - 1, 13)
    return start, end


def statement_cycle_end(statement_month: str) -> date:
    month = datetime.strptime(statement_month, "%B %Y")
    return date(month.year, month.month, 12)


def merchant_key(description: str) -> str:
    value = re.sub(r"\s+", " ", description.upper()).strip()
    return value.split(",")[0][:45]


def transaction_signature(day: date, amount: float, merchant: str) -> tuple[str, float, str]:
    return day.isoformat(), round(float(amount), 2), merchant_key(merchant)


def validated_statement_rows(statements_data: dict, validation: list[dict]) -> list[dict]:
    valid_months = {
        row["month"] for row in validation
        if row.get("validated") is True and row.get("month") != "Freshness / reconciliation gate"
    }
    return [row for row in statements_data.get("statements", []) if row.get("month") in valid_months]


def calculate_lifetime_spend(
    statements_data: dict,
    validation: list[dict],
    alerts: list[dict],
    activation_date: date,
) -> dict:
    statements = validated_statement_rows(statements_data, validation)
    if not statements:
        raise ValueError("No validated Airtel statements are available")
    latest_statement_end = max(statement_cycle_end(row["month"]) for row in statements)
    debits: dict[tuple[str, float, str], float] = {}
    credits: list[tuple[date, float, str]] = []
    for statement in statements:
        for tx in statement.get("transactions", []):
            try:
                day = parse_date(tx["date"])
                amount = round(float(tx["amount"]), 2)
            except (KeyError, TypeError, ValueError):
                continue
            if day < activation_date or day > latest_statement_end or amount <= 0:
                continue
            description = str(tx.get("description", ""))
            upper = description.upper()
            if upper.startswith("- ") or any(term in upper for term in EXCLUDED_DEBIT_TERMS):
                continue
            if tx.get("type") == "Dr":
                debits.setdefault(transaction_signature(day, amount, description), amount)
            elif tx.get("type") == "Cr" and not any(term in upper for term in EXCLUDED_CREDIT_TERMS):
                credits.append((day, amount, description))

    # Subtract only exact merchant-and-amount reversals that have a matching debit.
    for credit_day, amount, description in credits:
        key = merchant_key(description)
        match = next(
            (signature for signature in debits
             if signature[1] == amount and signature[2] == key and signature[0] <= credit_day.isoformat()),
            None,
        )
        if match:
            debits.pop(match)

    alert_signatures = set()
    alert_total = 0.0
    tracked_through = latest_statement_end
    for alert in alerts:
        try:
            day = parse_date(alert["date"])
            amount = round(float(alert["amount"]), 2)
        except (KeyError, TypeError, ValueError):
            continue
        if day <= latest_statement_end or day < activation_date or amount <= 0:
            continue
        subject = str(alert.get("subject", ""))
        message_id = alert.get("message_id") or alert.get("gmail_message_id")
        signature = ("id", message_id) if message_id else ("fallback",) + transaction_signature(day, amount, subject)
        if signature in alert_signatures:
            continue
        alert_signatures.add(signature)
        alert_total += amount
        tracked_through = max(tracked_through, day)

    return {
        "lifetime": round(sum(debits.values()) + alert_total, 2),
        "latest_statement_end": latest_statement_end,
        "tracked_through": tracked_through,
    }


def latest_confirmed_cycle(validation: list[dict], statements_data: dict) -> date:
    covered = []
    for statement in statements_data.get("statements", []):
        for tx in statement.get("transactions", []):
            match = re.search(r"CASHBACK CREDIT\s+([A-Z]{3})(\d{2})", str(tx.get("description", "")).upper())
            if match:
                month = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%b %y")
                covered.append(date(month.year, month.month, 12))
    if not covered:
        raise ValueError("No cashback-credit earning cycle could be established")
    return max(covered)


def cycle_cashback(transactions: list[tuple], classifications: list[dict]) -> float:
    categorized = classify_transactions(transactions, classifications)
    spend = {name: sum(float(tx["amount"]) for tx in categorized[name]) for name in ("airtel", "utilities", "merchants", "general")}
    return round(
        min(spend["airtel"] * .25, 250)
        + min(spend["utilities"] * .10, 250)
        + min(spend["merchants"] * .10, 500)
        + spend["general"] * .01,
        2,
    )


def calculate_lifetime_cashback(
    statements_data: dict,
    validation: list[dict],
    alerts: list[dict],
    classifications: list[dict],
    latest_statement_end: date,
) -> dict:
    confirmed = round(sum(
        float(row.get("cb_credited") or 0)
        for row in validation
        if row.get("validated") is True and row.get("cashback_verified") is True
    ), 2)
    confirmed_through = latest_confirmed_cycle(validation, statements_data)
    statements = validated_statement_rows(statements_data, validation)
    pending = round(sum(
        float(row.get("cashback_earned") or 0)
        for row in statements
        if statement_cycle_end(row["month"]) > confirmed_through
    ), 2)

    grouped = defaultdict(list)
    seen = set()
    for alert in alerts:
        try:
            day = parse_date(alert["date"])
            amount = round(float(alert["amount"]), 2)
        except (KeyError, TypeError, ValueError):
            continue
        if day <= latest_statement_end or amount <= 0:
            continue
        subject = str(alert.get("subject", ""))
        message_id = alert.get("message_id") or alert.get("gmail_message_id")
        signature = ("id", message_id) if message_id else ("fallback",) + transaction_signature(day, amount, subject)
        if signature in seen:
            continue
        seen.add(signature)
        grouped[cycle_bounds(day)].append((datetime.combine(day, datetime.min.time()), amount, subject.upper(), merchant_key(subject)))
    pending = round(pending + sum(cycle_cashback(rows, classifications) for rows in grouped.values()), 2)
    return {
        "confirmed": confirmed,
        "pending": pending,
        "lifetime": round(confirmed + pending, 2),
        "confirmed_through": confirmed_through,
    }


def evidence_run_id(metadata: dict) -> str:
    if metadata.get("run_id"):
        return str(metadata["run_id"])
    count = metadata.get("alert_count", metadata.get("unique_alert_count"))
    if not metadata.get("synced_at") or not isinstance(count, int) or not metadata.get("latest_alert_date"):
        raise ValueError("Airtel sync metadata is incomplete")
    raw = f"{metadata['synced_at']}|{count}|{metadata['latest_alert_date']}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]
