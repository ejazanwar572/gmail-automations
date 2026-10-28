#!/usr/bin/env python3
"""Shared benefit tracker primitives for new credit-card workflows."""

from __future__ import annotations

import json
import calendar
import math
import os
import re
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import card_freshness
from card_progress import render_milestone, render_progress_bar


MONEY_RE = re.compile(r"(?:INR|Rs\.?|₹)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.IGNORECASE)
DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_amount(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    match = MONEY_RE.search(str(value).replace(",", ""))
    return float(match.group(1)) if match else 0.0


def parse_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not value:
        return None
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def format_money(amount: float | int | None) -> str:
    if amount is None:
        return "Pending"
    return f"INR {float(amount):,.2f}"


def normalize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    raw = alert.get("raw") if isinstance(alert.get("raw"), dict) else alert
    amount = parse_amount(alert.get("amount") or alert.get("Amount"))
    parsed_date = parse_date(alert.get("date") or alert.get("Date"))
    subject = str(alert.get("subject") or alert.get("description") or alert.get("merchant") or "").strip()
    merchant = str(alert.get("merchant") or alert.get("payee") or subject or "Unknown").strip()
    normalized = {
        "date": parsed_date.isoformat() if parsed_date else "",
        "amount": amount,
        "subject": subject,
        "merchant": merchant,
        "raw": raw,
    }
    for field in (
        "message_id", "email_date", "source", "mcc", "currency", "country",
        "transaction_type", "direction", "is_contactless", "reversal_of",
        "cashback_confirmed", "classification_evidence",
    ):
        value = alert.get(field)
        if value is None:
            value = raw.get(field)
        if value is not None:
            normalized[field] = value
    return normalized


def load_config(card_dir: Path) -> dict[str, Any]:
    config = load_json(card_dir / "benefits_config.json", {})
    reward_model = config.get("reward_model")
    if isinstance(reward_model, dict) and reward_model.get("confirmed_statement_artifact"):
        artifact = load_json(card_dir / str(reward_model["confirmed_statement_artifact"]), {})
        required_fields = ("total_points", "base_points", "accelerated_points", "bonus_points")
        if artifact.get("scope") != "lifetime" or not artifact.get("statement_end"):
            raise ValueError("HDFC statement reward artifact must contain a lifetime scope and statement_end")
        if any(isinstance(artifact.get(field), bool) or not isinstance(artifact.get(field), int) for field in required_fields):
            raise ValueError("HDFC statement reward artifact contains invalid point totals")
        if artifact["base_points"] + artifact["accelerated_points"] + artifact["bonus_points"] != artifact["total_points"]:
            raise ValueError("HDFC statement reward artifact does not reconcile")
        reward_model["confirmed_statement"] = {
            "through": artifact["statement_end"],
            **{field: artifact[field] for field in required_fields},
        }
    return config


def load_alerts(card_dir: Path) -> list[dict[str, Any]]:
    payload = load_json(card_dir / "gmail_alerts.json", [])
    if isinstance(payload, dict):
        payload = payload.get("alerts", [])
    return [normalize_alert(alert) for alert in payload]


def _month_day(year: int, month: int, requested_day: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(max(1, requested_day), last_day))


def _add_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month_index = (year * 12 + (month - 1)) + delta
    return month_index // 12, month_index % 12 + 1


def cycle_window(config: dict[str, Any], as_of: date) -> tuple[date, date]:
    cycle = config.get("cycle", {})
    if cycle.get("start") and cycle.get("end"):
        start = parse_date(cycle["start"])
        end = parse_date(cycle["end"])
        if start and end:
            while as_of > end:
                next_year, next_month = _add_month(end.year, end.month, 1)
                start = end + timedelta(days=1)
                end = _month_day(next_year, next_month, end.day)
            return start, end
    if not cycle:
        return date(as_of.year, 1, 1), as_of

    close_day = int(cycle.get("statement_day") or cycle.get("close_day") or 30)
    current_close = _month_day(as_of.year, as_of.month, close_day)
    if as_of > current_close:
        start = current_close + timedelta(days=1)
        next_year, next_month = _add_month(as_of.year, as_of.month, 1)
        end = _month_day(next_year, next_month, close_day)
    else:
        previous_year, previous_month = _add_month(as_of.year, as_of.month, -1)
        previous_close = _month_day(previous_year, previous_month, close_day)
        start = previous_close + timedelta(days=1)
        end = current_close
    return start, end


def _matches(rule: dict[str, Any], alert: dict[str, Any]) -> bool:
    matchers = [str(token).upper() for token in rule.get("match", [])]
    if "DEFAULT" in matchers:
        return False
    haystack = " ".join(str(alert.get(key, "")) for key in ("subject", "merchant")).upper()
    return any(token and token in haystack for token in matchers)


def assign_rule(config: dict[str, Any], alert: dict[str, Any]) -> dict[str, Any] | None:
    alert_date = parse_date(alert.get("date"))
    if (
        "HSBC LIVE+" in str(config.get("card_name", "")).upper()
        and alert_date and alert_date >= date(2026, 7, 26)
        and any(token in " ".join(str(alert.get(key, "")) for key in ("subject", "merchant")).upper()
                for token in ("SHOPPING", "UTILITY", "UTILITIES"))
    ):
        return {
            "name": "10% Shopping and Utilities (Provisional)",
            "rate": 0.10,
            "monthly_cap": 1000,
            "match": ["SHOPPING", "UTILITY", "UTILITIES"],
            "provisional": True,
            "effective_from": "2026-07-26",
        }
    rules = config.get("benefit_rules", [])
    default_rule = None
    for rule in rules:
        matchers = [str(token).upper() for token in rule.get("match", [])]
        if "DEFAULT" in matchers:
            default_rule = rule
            continue
        if _matches(rule, alert):
            return rule
    return default_rule


def _is_hsbc_live_plus(config: dict[str, Any]) -> bool:
    return "HSBC LIVE+" in str(config.get("card_name", "")).upper()


def _hsbc_policy(config: dict[str, Any]) -> dict[str, Any] | None:
    policy = config.get("cashback_policy")
    return policy if _is_hsbc_live_plus(config) and isinstance(policy, dict) else None


def _hsbc_category_match(policy: dict[str, Any], alert: dict[str, Any]) -> tuple[str | None, str]:
    mcc = str(alert.get("mcc") or "").strip()
    haystack = " ".join(str(alert.get(key, "")) for key in ("subject", "merchant")).upper()
    categories = policy.get("categories", {})
    if not isinstance(categories, dict):
        return None, "unavailable"
    for label, definition in categories.items():
        if not isinstance(definition, dict):
            continue
        if mcc and mcc in {str(value) for value in definition.get("mccs", [])}:
            return str(label), "confirmed"
    for label, definition in categories.items():
        if not isinstance(definition, dict):
            continue
        if any(str(token).upper() in haystack for token in definition.get("keywords", []) if token):
            return str(label), "estimated"
    return None, "unavailable"


def _hsbc_is_international(alert: dict[str, Any]) -> bool:
    currency = str(alert.get("currency") or "").strip().upper()
    country = str(alert.get("country") or "").strip().upper()
    return bool((currency and currency not in {"INR", "₹"}) or (country and country not in {"IN", "IND", "INDIA"}))


def _hsbc_post_policy_classification(
    policy: dict[str, Any], alert: dict[str, Any], alert_date: date
) -> tuple[str, float, str]:
    mcc = str(alert.get("mcc") or "").strip()
    fuel_mccs = {
        str(value) for value in (policy.get("fuel_offer") or {}).get("eligible_mccs", [])
    }
    if _hsbc_is_international(alert) or mcc in {str(value) for value in policy.get("excluded_mccs", [])} or mcc in fuel_mccs:
        return "Excluded", 0.0, "confirmed" if mcc or alert.get("currency") or alert.get("country") else "estimated"
    category, evidence_status = _hsbc_category_match(policy, alert)
    merchant = str(alert.get("merchant") or "").upper()
    overrides = policy.get("merchant_overrides", {})
    temporary_overrides = overrides.get("temporary_accelerated", []) if isinstance(overrides, dict) else []
    for override in temporary_overrides:
        if not isinstance(override, dict):
            continue
        through = parse_date(override.get("through"))
        if str(override.get("merchant") or "").upper() in merchant and through and alert_date <= through:
            return str(override.get("category") or category or "Shopping"), float(policy["accelerated_rate"]), evidence_status
    if category == "Shopping" and any(
        isinstance(override, dict)
        and str(override.get("merchant") or "").upper() in merchant
        and (through := parse_date(override.get("through"))) is not None
        and alert_date > through
        for override in temporary_overrides
    ):
        return "1.5% Other Eligible Spends", float(policy["standard_rate"]), evidence_status
    if category == "Shopping" and isinstance(overrides, dict) and any(
        str(token).upper() in merchant for token in overrides.get("standard", [])
    ):
        return "1.5% Other Eligible Spends", float(policy["standard_rate"]), evidence_status
    if category:
        return category, float(policy["accelerated_rate"]), evidence_status
    if mcc:
        return "1.5% Other Eligible Spends", float(policy["standard_rate"]), "confirmed"
    return "Unclassified", 0.0, "unavailable"


def _hsbc_fuel_offer(policy: dict[str, Any], alerts: list[dict[str, Any]], as_of: date) -> dict[str, Any] | None:
    offer = policy.get("fuel_offer")
    if not isinstance(offer, dict):
        return None
    effective_from = parse_date(offer.get("effective_from"))
    ends_on = parse_date(offer.get("ends_on"))
    if effective_from is None or ends_on is None:
        raise ValueError("HSBC fuel offer dates are invalid")
    quarter_start_month = ((as_of.month - 1) // 3) * 3 + 1
    quarter_start = date(as_of.year, quarter_start_month, 1)
    quarter_end_month = quarter_start_month + 2
    quarter_end = date(as_of.year, quarter_end_month, calendar.monthrange(as_of.year, quarter_end_month)[1])
    deadline = min(quarter_end, ends_on)
    mccs = {str(value) for value in offer.get("eligible_mccs", [])}
    minimum = float(offer.get("minimum_transaction", 0) or 0)
    maximum = float(offer.get("maximum_transaction", 0) or 0)
    qualifying = [
        alert for alert in alerts
        if (alert_date := parse_date(alert.get("date"))) is not None
        and max(quarter_start, effective_from) <= alert_date <= deadline
        and str(alert.get("mcc") or "") in mccs
        and alert.get("is_contactless") is True
        and not _hsbc_is_international(alert)
        and minimum <= float(alert["amount"]) <= maximum
    ]
    target = float(offer.get("quarterly_target", 0) or 0)
    progress = round(sum(alert["amount"] for alert in qualifying), 2)
    return {
        "id": "fuel-contactless",
        "label": "Contactless fuel offer",
        "progress": progress,
        "target": target,
        "remaining": round(max(0.0, target - progress), 2),
        "percent": min(100.0, round((progress / target) * 100, 1)) if target else 0.0,
        "reward": float(offer.get("reward", 0) or 0),
        "status": "Met" if target and progress >= target else "In progress",
        "period_start": max(quarter_start, effective_from).isoformat(),
        "deadline": deadline.isoformat(),
        "days_left": max(0, (deadline - as_of).days),
        "offer_ends_on": ends_on.isoformat(),
        "source_conflict": bool(offer.get("source_conflict")),
        "evidence_status": "confirmed" if qualifying else "unavailable",
    }


def _hsbc_lounge_entitlements(policy: dict[str, Any], as_of: date) -> list[dict[str, Any]]:
    lounge = policy.get("lounge")
    if not isinstance(lounge, dict):
        return []
    year = as_of.year
    international_from = parse_date(lounge.get("international_available_from"))
    return [
        {
            "id": "domestic-h1", "label": "Domestic lounge · Jan–Jun",
            "allowance": int(lounge.get("domestic_per_half_year", 1)),
            "used": None, "remaining": None, "period_start": f"{year}-01-01",
            "period_end": f"{year}-06-30", "available": as_of <= date(year, 6, 30),
            "evidence_status": "unavailable",
        },
        {
            "id": "domestic-h2", "label": "Domestic lounge · Jul–Dec",
            "allowance": int(lounge.get("domestic_per_half_year", 1)),
            "used": None, "remaining": None, "period_start": f"{year}-07-01",
            "period_end": f"{year}-12-31", "available": as_of >= date(year, 7, 1),
            "evidence_status": "unavailable",
        },
        {
            "id": "international", "label": "International lounge",
            "allowance": int(lounge.get("international_annual", 1)),
            "used": None, "remaining": None,
            "period_start": international_from.isoformat() if international_from else f"{year}-01-01",
            "period_end": f"{year}-12-31",
            "available": bool(international_from and as_of >= international_from),
            "evidence_status": "unavailable",
        },
    ]


def calculate_hsbc_cashback_summary(
    config: dict[str, Any], alerts: list[dict[str, Any]], as_of: date
) -> dict[str, Any] | None:
    policy = _hsbc_policy(config)
    if policy is None:
        return None
    effective_from = parse_date(policy.get("effective_from"))
    if effective_from is None:
        raise ValueError("HSBC cashback policy effective_from is invalid")
    accelerated_rate = float(policy.get("accelerated_rate", 0.0) or 0.0)
    accelerated_cap = float(policy.get("accelerated_cap", 0.0) or 0.0)
    standard_rate = float(policy.get("standard_rate", 0.0) or 0.0)
    if accelerated_rate <= 0 or accelerated_cap <= 0 or standard_rate < 0:
        raise ValueError("HSBC cashback policy rates or cap are invalid")

    deduplicated = _deduplicated_alerts(alerts)
    reversal_types = {"reversal", "refund", "credit"}
    reversals = [
        alert for alert in deduplicated
        if str(alert.get("transaction_type") or alert.get("direction") or "").strip().lower() in reversal_types
    ]
    reversed_message_ids = {
        str(alert["reversal_of"]) for alert in reversals if alert.get("reversal_of")
    }
    effective_alerts = [
        alert for alert in deduplicated
        if alert not in reversals and str(alert.get("message_id") or "") not in reversed_message_ids
    ]
    cycle_alerts = filter_cycle_alerts(config, effective_alerts, as_of)
    categories = {
        str(label): {
            "name": str(label), "rate": accelerated_rate, "cap": None,
            "spend": 0.0, "earned_before_cap": 0.0, "earned": 0.0,
            "remaining_cap": None, "count": 0, "provisional": False,
            "cap_group_id": "accelerated-live-plus", "evidence_status": "unavailable",
        }
        for label in policy.get("categories", {})
    }
    other_name = "1.5% Other Eligible Spends"
    categories[other_name] = {
        "name": other_name, "rate": standard_rate, "cap": None,
        "spend": 0.0, "earned_before_cap": 0.0, "earned": 0.0,
        "remaining_cap": None, "count": 0, "provisional": False,
        "cap_group_id": None, "evidence_status": "unavailable",
    }

    def classify(alert: dict[str, Any]) -> dict[str, Any]:
        alert_date = parse_date(alert.get("date"))
        category = None
        evidence_status = "unavailable"
        rate = 0.0
        if alert_date and alert_date >= effective_from:
            category, rate, evidence_status = _hsbc_post_policy_classification(policy, alert, alert_date)
        else:
            legacy_rule = assign_rule(config, alert)
            if legacy_rule and legacy_rule.get("monthly_cap") is not None:
                category, evidence_status = _hsbc_category_match(policy, alert)
                rate = accelerated_rate if category else 0.0
            elif legacy_rule:
                category, evidence_status, rate = other_name, "estimated", standard_rate
        if category in (None, "Unclassified", "Excluded"):
            final_category = category or "Unclassified"
            return {**alert, "category": final_category, "rate": 0.0, "evidence_status": evidence_status}
        return {**alert, "category": category, "rate": rate, "evidence_status": evidence_status}

    classified: list[dict[str, Any]] = []
    for alert in sorted(cycle_alerts, key=lambda item: (item.get("date", ""), item.get("message_id", ""))):
        classified_alert = classify(alert)
        category = classified_alert["category"]
        evidence_status = classified_alert["evidence_status"]
        rate = classified_alert["rate"]
        classified.append(classified_alert)
        if category in ("Unclassified", "Excluded"):
            continue
        bucket = categories[category]
        bucket["spend"] += alert["amount"]
        bucket["earned_before_cap"] += alert["amount"] * rate
        bucket["count"] += 1
        bucket["evidence_status"] = (
            "estimated" if "estimated" in (bucket["evidence_status"], evidence_status)
            else evidence_status
        )

    cap_remaining = accelerated_cap
    for alert in classified:
        category = alert["category"]
        if category not in categories:
            continue
        bucket = categories[category]
        potential = alert["amount"] * alert["rate"]
        if bucket.get("cap_group_id"):
            awarded = min(cap_remaining, potential)
            cap_remaining -= awarded
        else:
            awarded = potential
        bucket["earned"] += awarded
    for bucket in categories.values():
        for field in ("spend", "earned_before_cap", "earned"):
            bucket[field] = round(bucket[field], 2)

    earned = round(accelerated_cap - cap_remaining, 2)
    activation_date = parse_date(config.get("welcome", {}).get("activation_proxy_date"))
    lifetime_alerts = [
        alert for alert in effective_alerts
        if (alert_date := parse_date(alert.get("date"))) is not None
        and (activation_date is None or alert_date >= activation_date)
        and alert_date <= as_of
    ]
    lifetime_classified = [
        classify(alert) for alert in sorted(
            lifetime_alerts, key=lambda item: (item.get("date", ""), item.get("message_id", ""))
        )
    ]
    cycle_cap_remaining: dict[tuple[str, str], float] = {}
    lifetime_cashback = 0.0
    for alert in lifetime_classified:
        if alert["category"] in ("Unclassified", "Excluded"):
            continue
        potential = alert["amount"] * alert["rate"]
        if alert["category"] == other_name:
            lifetime_cashback += potential
            continue
        alert_date = parse_date(alert["date"])
        cycle_start, cycle_end = cycle_window(config, alert_date)
        cycle_key = (cycle_start.isoformat(), cycle_end.isoformat())
        available = cycle_cap_remaining.setdefault(cycle_key, accelerated_cap)
        awarded = min(available, potential)
        cycle_cap_remaining[cycle_key] = max(0.0, available - awarded)
        lifetime_cashback += awarded
    current_cashback = round(sum(bucket["earned"] for bucket in categories.values()), 2)
    lifetime_cashback = round(lifetime_cashback, 2)
    confirmed_cashback = round(sum(
        float(alert.get("cashback_confirmed") or 0.0) for alert in lifetime_alerts
    ), 2)
    pending_cashback = round(max(0.0, lifetime_cashback - confirmed_cashback), 2)
    unclassified = [alert for alert in classified if alert["category"] == "Unclassified"]
    classified_eligible = [
        alert for alert in classified if alert["category"] not in ("Unclassified", "Excluded")
    ]
    tracked_dates = [parse_date(alert.get("date")) for alert in lifetime_alerts]
    tracked_dates = [value for value in tracked_dates if value is not None]
    cycle_start, cycle_end = cycle_window(config, as_of)
    return {
        "policy": {
            "version": str(policy.get("version") or policy["effective_from"]),
            "effective_from": effective_from.isoformat(),
            "reviewed_at": policy.get("reviewed_at"),
            "sources": policy.get("sources", []),
        },
        "shared_cap": {
            "id": "accelerated-live-plus",
            "label": "10% accelerated cashback",
            "cap": round(accelerated_cap, 2),
            "earned": earned,
            "remaining": round(max(0.0, cap_remaining), 2),
            "period_start": cycle_start.isoformat(),
            "period_end": cycle_end.isoformat(),
            "reset_date": (cycle_end + timedelta(days=1)).isoformat(),
            "evidence_status": (
                "unavailable" if not classified_eligible
                else "estimated" if any(row["evidence_status"] == "estimated" for row in classified_eligible)
                else "confirmed"
            ),
            "bucket_ids": [name for name in categories if name != other_name],
        },
        "benefits": categories,
        "classified_transactions": classified,
        "effective_transactions": effective_alerts,
        "period_totals": {
            "spend": {
                "lifetime": round(sum(alert["amount"] for alert in lifetime_alerts), 2),
                "current_cycle": round(sum(alert["amount"] for alert in cycle_alerts), 2),
                "lifetime_start": activation_date.isoformat() if activation_date else None,
                "tracked_through": max(tracked_dates).isoformat() if tracked_dates else None,
                "evidence_status": "estimated" if lifetime_alerts else "unavailable",
            },
            "cashback": {
                "lifetime": lifetime_cashback,
                "current_cycle": current_cashback,
                "confirmed": confirmed_cashback,
                "pending": pending_cashback,
                "confirmed_through": None,
                "evidence_status": (
                    "mixed" if confirmed_cashback and pending_cashback
                    else "confirmed" if confirmed_cashback
                    else "estimated" if lifetime_alerts
                    else "unavailable"
                ),
            },
        },
        "unclassified": {
            "spend": round(sum(alert["amount"] for alert in unclassified), 2),
            "transactions": len(unclassified),
        },
        "limited_offers": {"fuel": _hsbc_fuel_offer(policy, effective_alerts, as_of)},
        "entitlements": {"lounges": _hsbc_lounge_entitlements(policy, as_of)},
    }


def filter_cycle_alerts(config: dict[str, Any], alerts: list[dict[str, Any]], as_of: date) -> list[dict[str, Any]]:
    start, end = cycle_window(config, as_of)
    cycle_alerts = []
    for alert in alerts:
        alert_date = parse_date(alert.get("date"))
        if alert_date is None or start <= alert_date <= end:
            cycle_alerts.append(alert)
    return cycle_alerts


IST = ZoneInfo("Asia/Kolkata")


def _deduplicated_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the first alert for each issuer message, with a stable fallback for legacy data."""
    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for alert in alerts:
        message_id = alert.get("message_id")
        key = ("message", message_id) if message_id else (
            "legacy", alert.get("date"), alert.get("amount"), alert.get("merchant"), alert.get("subject"),
        )
        if key not in seen:
            seen.add(key)
            deduplicated.append(alert)
    return deduplicated


def _ist_date(alert: dict[str, Any]) -> date | None:
    raw = alert.get("email_date") or alert.get("date")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return parse_date(raw)
    if parsed.tzinfo is None:
        return parsed.date()
    return parsed.astimezone(IST).date()


def _smartbuy_classifications(reward_cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    configured = reward_cfg.get("smartbuy_classifications", {})
    if isinstance(configured, dict):
        rows = configured.values()
    elif isinstance(configured, list):
        rows = configured
    else:
        rows = []
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("message_id"), str) and row["message_id"]:
            result[row["message_id"]] = row
    return result


def calculate_hdfc_reward_summary(config: dict[str, Any], alerts: list[dict[str, Any]], as_of: date) -> dict[str, Any]:
    """Build a statement-safe HDFC lifetime and monthly SmartBuy points summary.

    Statement points are the confirmed lifetime baseline. Only transaction-level
    estimates after that statement's end date are added, preventing historic
    points from being reset or counted twice.
    """
    reward_cfg = config.get("reward_model") or {}
    activation_date = parse_date(config.get("welcome", {}).get("activation_proxy_date"))
    transactions = [
        alert for alert in _deduplicated_alerts([normalize_alert(alert) for alert in alerts])
        if (transaction_date := _ist_date(alert)) is not None and (activation_date is None or transaction_date >= activation_date)
    ]
    # Preserve the IST-normalized date for every calculation below.
    dated_transactions = [(alert, _ist_date(alert)) for alert in transactions]
    base_per_block = int(reward_cfg.get("base_points_per_150", 0) or 0)
    classifications = _smartbuy_classifications(reward_cfg)
    statement = reward_cfg.get("confirmed_statement") if isinstance(reward_cfg.get("confirmed_statement"), dict) else None
    statement_end = parse_date(statement.get("through")) if statement else None

    def points_for(alert: dict[str, Any]) -> tuple[int, int]:
        classification = classifications.get(alert.get("message_id"))
        reward_eligible = isinstance(classification, dict) and classification.get("reward_eligible") is True
        blocks = math.floor(float(alert["amount"]) / 150.0)
        base = blocks * base_per_block if reward_eligible else 0
        multiplier = (
            int(classification.get("accelerated_multiplier", 0) or 0)
            if isinstance(classification, dict) else 0
        )
        accelerated = base * multiplier
        return base, accelerated

    accelerated_cap = int(reward_cfg.get("accelerated_monthly_cap", 0) or 0)
    confirmed_fields = ("total_points", "base_points", "accelerated_points", "bonus_points")
    statement_confirmed = bool(statement_end and statement and all(isinstance(statement.get(field), int) for field in confirmed_fields))
    post_statement = [
        (alert, when) for alert, when in dated_transactions
        if statement_end is None or when > statement_end
    ]
    post_base = sum(points_for(alert)[0] for alert, _ in post_statement)
    all_base = sum(points_for(alert)[0] for alert, _ in dated_transactions)

    def accelerated_by_month(rows: list[tuple[dict[str, Any], date]]) -> dict[tuple[int, int], int]:
        totals: dict[tuple[int, int], int] = {}
        for alert, when in rows:
            key = (when.year, when.month)
            totals[key] = totals.get(key, 0) + points_for(alert)[1]
        return totals

    confirmed_rows = [
        (alert, when) for alert, when in dated_transactions
        if statement_confirmed and when <= statement_end
    ]
    confirmed_by_month = accelerated_by_month(confirmed_rows)
    post_by_month = accelerated_by_month(post_statement)
    post_accelerated = sum(
        min(raw, max(0, accelerated_cap - confirmed_by_month.get(month, 0)))
        for month, raw in post_by_month.items()
    )
    all_accelerated = sum(
        min(raw, accelerated_cap) for raw in accelerated_by_month(dated_transactions).values()
    )
    if statement_confirmed:
        lifetime_points = {
            "total": statement["total_points"] + post_base + post_accelerated,
            "base": statement["base_points"] + post_base,
            "accelerated": statement["accelerated_points"] + post_accelerated,
            "bonus": statement["bonus_points"],
            "evidence_status": "mixed" if post_base or post_accelerated else "confirmed",
        }
    else:
        lifetime_points = {
            "total": all_base + all_accelerated,
            "base": all_base,
            "accelerated": all_accelerated,
            "bonus": 0,
            "evidence_status": "estimated" if dated_transactions else "unavailable",
        }

    month_start = date(as_of.year, as_of.month, 1)
    month_end = date(as_of.year, as_of.month, calendar.monthrange(as_of.year, as_of.month)[1])
    reset_date = month_end + timedelta(days=1)
    classified_month = [
        (alert, when) for alert, when in dated_transactions
        if month_start <= when <= month_end and alert.get("message_id") in classifications
    ]
    confirmed_month_accelerated = sum(
        points_for(alert)[1] for alert, when in classified_month
        if statement_confirmed and when <= statement_end
    )
    raw_estimated_month_accelerated = sum(
        points_for(alert)[1] for alert, when in classified_month
        if not statement_confirmed or when > statement_end
    )
    estimated_month_accelerated = min(
        raw_estimated_month_accelerated,
        max(0, accelerated_cap - confirmed_month_accelerated),
    )
    raw_month_accelerated = confirmed_month_accelerated + estimated_month_accelerated
    if not classified_month:
        cap_evidence = "unavailable"
    elif statement_confirmed and estimated_month_accelerated:
        cap_evidence = "mixed"
    elif statement_confirmed:
        cap_evidence = "confirmed"
    else:
        cap_evidence = "estimated"
    earned = min(accelerated_cap, raw_month_accelerated)
    remaining = max(0, accelerated_cap - earned)
    return {
        "lifetime_spend": round(sum(alert["amount"] for alert, _ in dated_transactions), 2),
        "lifetime_points": lifetime_points,
        "statement_through": statement_end.isoformat() if statement_end else None,
        "post_statement_points": {"base": post_base, "accelerated": post_accelerated},
        "accelerated_cap": {
            "cap": accelerated_cap, "earned": earned, "remaining": remaining,
            "remaining_percent": round((remaining / accelerated_cap) * 100, 1) if accelerated_cap else 0.0,
            "month_start": month_start.isoformat(), "month_end": month_end.isoformat(),
            "reset_date": reset_date.isoformat(), "days_remaining": max(0, (month_end - as_of).days),
            "evidence_status": cap_evidence,
        },
        # Keep existing Markdown rendering compatible while exposing the richer contract above.
        "base_points": lifetime_points["base"],
    }


def calculate_benefits(config: dict[str, Any], alerts: list[dict[str, Any]], as_of: date | None = None) -> dict[str, Any]:
    as_of = as_of or date.today()
    normalized_alerts = [normalize_alert(alert) for alert in alerts]
    hsbc_cashback = calculate_hsbc_cashback_summary(config, normalized_alerts, as_of)
    accounting_alerts = hsbc_cashback["effective_transactions"] if hsbc_cashback is not None else normalized_alerts
    cycle_alerts = filter_cycle_alerts(config, accounting_alerts, as_of)
    total_spend = sum(alert["amount"] for alert in cycle_alerts)
    annual_cfg = config.get("annual_fee", {})
    annual_start = parse_date(annual_cfg.get("period_start"))
    annual_end = parse_date(annual_cfg.get("period_end"))
    annual_spend = sum(
        alert["amount"] for alert in accounting_alerts
        if (parsed := parse_date(alert.get("date"))) is not None
        and (annual_start is None or parsed >= annual_start)
        and (annual_end is None or parsed <= annual_end)
    )

    if hsbc_cashback is not None:
        benefits = hsbc_cashback["benefits"]
    else:
        benefits: dict[str, dict[str, Any]] = {}
        for alert in cycle_alerts:
            rule = assign_rule(config, alert)
            if not rule:
                continue
            name = rule.get("name", "Eligible Spends")
            bucket = benefits.setdefault(
                name,
                {
                    "name": name,
                    "rate": float(rule.get("rate", 0.0) or 0.0),
                    "cap": rule.get("monthly_cap"),
                    "spend": 0.0,
                    "earned_before_cap": 0.0,
                    "earned": 0.0,
                    "remaining_cap": None,
                    "count": 0,
                    "provisional": bool(rule.get("provisional", False)),
                },
            )
            bucket["spend"] += alert["amount"]
            bucket["earned_before_cap"] += alert["amount"] * bucket["rate"]
            bucket["count"] += 1

        for bucket in benefits.values():
            cap = bucket.get("cap")
            if cap is None:
                bucket["earned"] = round(bucket["earned_before_cap"], 2)
                bucket["remaining_cap"] = None
            else:
                bucket["earned"] = round(min(float(cap), bucket["earned_before_cap"]), 2)
                bucket["remaining_cap"] = round(max(0.0, float(cap) - bucket["earned"]), 2)
            bucket["spend"] = round(bucket["spend"], 2)
            bucket["earned_before_cap"] = round(bucket["earned_before_cap"], 2)

    welcome_cfg = config.get("welcome", {})
    welcome_target = welcome_cfg.get("spend_target")
    welcome_start = parse_date(welcome_cfg.get("activation_proxy_date"))
    welcome_days = welcome_cfg.get("window_days")
    welcome_end = welcome_start + timedelta(days=int(welcome_days)) if welcome_start and welcome_days else None
    if "HSBC LIVE+" in str(config.get("card_name", "")).upper():
        required_evidence = {
            "activation_proxy_date": welcome_start,
            "deadline": welcome_end,
            "evidence_state": welcome_cfg.get("evidence_state"),
            "activation_proxy_source": welcome_cfg.get("activation_proxy_source"),
        }
        missing = [name for name, value in required_evidence.items() if not value]
        if missing:
            raise ValueError(f"HSBC welcome evidence is incomplete: {', '.join(missing)}")
    welcome_spend = sum(
        alert["amount"] for alert in accounting_alerts
        if (parsed := parse_date(alert.get("date"))) is not None
        and (welcome_start is None or parsed >= welcome_start)
        and (welcome_end is None or parsed < welcome_end)
    )
    welcome = {
        "target": welcome_target,
        "spend": round(welcome_spend, 2),
        "remaining": None if welcome_target is None else round(max(0.0, float(welcome_target) - welcome_spend), 2),
        "status": "Pending setup" if welcome_target is None else ("Met" if welcome_spend >= float(welcome_target) else "In progress"),
        "notes": welcome_cfg.get("notes", []),
        "reward": welcome_cfg.get("reward"),
        "activation_date": welcome_start.isoformat() if welcome_start else None,
        "deadline": welcome_end.isoformat() if welcome_end else None,
        "evidence_state": welcome_cfg.get("evidence_state"),
        "evidence_source": welcome_cfg.get("activation_proxy_source"),
    }

    annual_fee_cfg = config.get("annual_fee", {})
    waiver_spend = annual_fee_cfg.get("waiver_spend")
    annual_fee = {
        "amount": annual_fee_cfg.get("amount"),
        "waiver_spend": waiver_spend,
        "period_start": annual_start.isoformat() if annual_start else None,
        "period_end": annual_end.isoformat() if annual_end else None,
        "eligible_spend": round(annual_spend, 2),
        "remaining_spend_for_waiver": None if waiver_spend is None else round(max(0.0, float(waiver_spend) - annual_spend), 2),
        "status": "Pending variant confirmation" if waiver_spend is None else ("Met" if annual_spend >= float(waiver_spend) else "In progress"),
    }

    reward_points = None
    reward_cfg = config.get("reward_model") or {}
    if "HDFC DINERS BLACK METAL" in str(config.get("card_name", "")).upper():
        reward_points = calculate_hdfc_reward_summary(config, normalized_alerts, as_of)
    elif reward_cfg.get("base_points_per_150"):
        base_points = math.floor(total_spend / 150.0) * float(reward_cfg["base_points_per_150"])
        reward_points = {
            "base_points": int(base_points),
            "smartbuy_value": round(base_points * float(reward_cfg.get("smartbuy_value_per_point", 0.0)), 2),
            "airmile_value": round(base_points * float(reward_cfg.get("airmile_value_per_point", 0.0)), 2),
            "voucher_value": round(base_points * float(reward_cfg.get("voucher_value_per_point", 0.0)), 2),
            "cashback_value": round(base_points * float(reward_cfg.get("cashback_value_per_point", 0.0)), 2),
        }

    quarterly_bonus = None
    quarterly_cfg = config.get("quarterly_bonus") or {}
    quarterly_target = quarterly_cfg.get("spend_target")
    if quarterly_target:
        quarter_start_month = ((as_of.month - 1) // 3) * 3 + 1
        quarter_start = date(as_of.year, quarter_start_month, 1)
        quarter_end_month = quarter_start_month + 2
        quarter_end = date(as_of.year, quarter_end_month, calendar.monthrange(as_of.year, quarter_end_month)[1])
        quarter_spend = sum(
            alert["amount"] for alert in normalized_alerts
            if (parsed := parse_date(alert.get("date"))) is not None and quarter_start <= parsed <= quarter_end
        )
        quarterly_bonus = {
            "spend": round(quarter_spend, 2),
            "target": float(quarterly_target),
            "remaining": round(max(0.0, float(quarterly_target) - quarter_spend), 2),
            "status": "Met" if quarter_spend >= float(quarterly_target) else "In progress",
            "period_start": quarter_start.isoformat(),
            "deadline": quarter_end.isoformat(),
            "bonus_points": int(quarterly_cfg.get("bonus_points", 0)),
        }

    variant_status = config.get("variant_status", "confirmed")
    recommendations_disabled = variant_status != "confirmed"
    recommendation_note = ""
    if recommendations_disabled:
        recommendation_note = "Reward recommendations disabled because the SBI variant is not confirmed."
    elif reward_points:
        recommendation_note = "Use this card where high-value travel or partner redemptions beat direct cashback alternatives."
    else:
        capped = [b for b in benefits.values() if b.get("cap") is not None and b.get("remaining_cap") == 0]
        recommendation_note = "Accelerated cap is exhausted; route additional accelerated-category spends to the next-best card." if capped else "Keep using this card for categories where the tracked benefit rate is strongest."

    result = {
        "as_of": as_of.isoformat(),
        "card_name": config.get("card_name", "Credit Card"),
        "card_ending": config.get("card_ending", ""),
        "variant_status": variant_status,
        "recommendations_disabled": recommendations_disabled,
        "recommendation_note": recommendation_note,
        "cycle_start": cycle_window(config, as_of)[0].isoformat(),
        "cycle_end": cycle_window(config, as_of)[1].isoformat(),
        "alerts": cycle_alerts,
        "total_spend": round(total_spend, 2),
        "annual_spend": round(annual_spend, 2),
        "benefits": benefits,
        "welcome": welcome,
        "annual_fee": annual_fee,
        "reward_points": reward_points,
        "quarterly_bonus": quarterly_bonus,
    }
    if hsbc_cashback is not None:
        result.update({
            "policy": hsbc_cashback["policy"],
            "shared_cap": hsbc_cashback["shared_cap"],
            "classified_transactions": hsbc_cashback["classified_transactions"],
            "period_totals": hsbc_cashback["period_totals"],
            "unclassified": hsbc_cashback["unclassified"],
            "limited_offers": hsbc_cashback["limited_offers"],
            "entitlements": hsbc_cashback["entitlements"],
        })
    return result


def render_sources(config: dict[str, Any]) -> str:
    sources = config.get("sources", [])
    if not sources:
        return "- No source URLs configured."
    lines = []
    for source in sources:
        label = source.get("label", "Source")
        url = source.get("url", "")
        note = source.get("note", "")
        tail = f" - {note}" if note else ""
        lines.append(f"- [{label}]({url}){tail}")
    return "\n".join(lines)


def build_report(card_dir: Path | str, as_of: date | None = None) -> str:
    card_dir = Path(card_dir)
    config = load_config(card_dir)
    alerts = load_alerts(card_dir)
    as_of = as_of or date.today()
    summary = calculate_benefits(config, alerts, as_of=as_of)
    title = f"# {summary['card_name']}: Benefit Tracker Report"
    lines = [title, ""]

    freshness = card_freshness.freshness_summary(card_dir)
    evidence_state = "pending" if summary["variant_status"] != "confirmed" else "verified"
    lines.extend([
        "## 1. Executive Summary",
        f"- Card ending: {summary['card_ending'] or 'Unknown'}",
        f"- Current cycle: {summary['cycle_start']} to {summary['cycle_end']}",
        f"- Current cycle tracked spend: {format_money(summary['total_spend'])}",
        f"- Data freshness: {freshness}",
    ])
    if "HSBC LIVE+" not in summary["card_name"].upper():
        lines.insert(4, f"- Variant status: {summary['variant_status']}")
    if "HSBC LIVE+" not in summary["card_name"].upper() and config.get("cycle", {}).get("source"):
        lines.append(f"- Cycle source: {config['cycle']['source']}")
    if summary["recommendations_disabled"]:
        lines.append(f"- Warning: {summary['recommendation_note']}")
    lines.append("")

    fee = summary["annual_fee"]
    fee_cfg = config.get("annual_fee", {})
    fee_period_start = parse_date(fee_cfg.get("period_start"))
    fee_deadline = parse_date(fee_cfg.get("period_end"))
    fee_period = (
        f"{fee_period_start.isoformat()} to {fee_deadline.isoformat()}"
        if fee_period_start and fee_deadline
        else None
    )
    fee_supporting_lines = [f"Annual/joining fee tracked: {format_money(fee['amount'])}"]
    if fee_cfg.get("evidence_source"):
        fee_supporting_lines.append(f"Evidence source: {fee_cfg['evidence_source']}")
    lines.extend([
        "## 2. Fee and Waiver Tracker",
        render_milestone(
            current=fee["eligible_spend"],
            target=fee["waiver_spend"],
            format_value=format_money,
            evidence_state=fee_cfg.get("evidence_state", evidence_state),
            period=fee_period,
            deadline=fee_deadline,
            as_of=as_of,
            supporting_lines=tuple(fee_supporting_lines),
        ),
        "",
    ])

    welcome = summary["welcome"]
    welcome_cfg = config.get("welcome", {})
    welcome_start = parse_date(welcome_cfg.get("activation_proxy_date"))
    welcome_window_days = welcome_cfg.get("window_days")
    welcome_deadline = (
        welcome_start + timedelta(days=int(welcome_window_days))
        if welcome_start and welcome_window_days
        else None
    )
    welcome_period = (
        f"{welcome_start.isoformat()} to {welcome_deadline.isoformat()}"
        if welcome_start and welcome_deadline
        else None
    )
    welcome_evidence_state = welcome_cfg.get("evidence_state", evidence_state)
    welcome_supporting_lines = ()
    if welcome_cfg.get("activation_proxy_source"):
        welcome_supporting_lines = (f"Activation proxy: {welcome_cfg['activation_proxy_source']}",)
    lines.extend([
        "## 3. Welcome Benefit Tracker",
        render_milestone(
            current=welcome["spend"],
            target=welcome["target"],
            format_value=format_money,
            evidence_state=welcome_evidence_state,
            period=welcome_period,
            deadline=welcome_deadline,
            as_of=as_of,
            supporting_lines=welcome_supporting_lines,
        ),
    ])
    for note in welcome.get("notes", []):
        lines.append(f"- {note}")
    lines.append("")

    quarterly = config.get("quarterly_bonus")
    transaction_section = 4
    if quarterly and summary["variant_status"] == "confirmed":
        quarter_start_month = ((as_of.month - 1) // 3) * 3 + 1
        quarter_start = date(as_of.year, quarter_start_month, 1)
        quarter_end_month = quarter_start_month + 2
        quarter_end = date(as_of.year, quarter_end_month, calendar.monthrange(as_of.year, quarter_end_month)[1])
        quarter_spend = sum(
            alert["amount"]
            for alert in summary["alerts"]
            if (parsed := parse_date(alert["date"])) and quarter_start <= parsed <= quarter_end
        )
        lines.extend([
            "## 4. Quarterly Bonus Tracker",
            render_milestone(
                current=quarter_spend,
                target=quarterly.get("spend_target"),
                format_value=format_money,
                evidence_state="provisional",
                period=f"{quarter_start.isoformat()} to {quarter_end.isoformat()}",
                deadline=quarter_end,
                as_of=as_of,
                supporting_lines=(f"Bonus on target: {quarterly.get('bonus_points', 0):,} reward points",),
            ),
            "",
        ])
        transaction_section = 5

    lines.extend([
        f"## {transaction_section}. Current Cycle Transaction Table",
        "| Date | Merchant | Amount | Benefit Bucket |",
        "| :--- | :--- | ---: | :--- |",
    ])
    transaction_alerts = summary["alerts"]
    classified_by_message = {
        row.get("message_id"): row
        for row in summary.get("classified_transactions", [])
        if row.get("message_id")
    }
    if config.get("transaction_order") == "desc":
        transaction_alerts = sorted(
            transaction_alerts,
            key=lambda alert: parse_date(alert.get("date")) or date.min,
            reverse=True,
        )
    for alert in transaction_alerts:
        classified = classified_by_message.get(alert.get("message_id"))
        if classified:
            bucket = classified.get("category", "Unclassified")
        else:
            rule = assign_rule(config, alert)
            bucket = rule.get("name", "Unclassified") if rule else "Unclassified"
        lines.append(f"| {alert['date'] or 'Unknown'} | {alert['merchant']} | {format_money(alert['amount'])} | {bucket} |")
    if not summary["alerts"]:
        lines.append("| - | No tracked transactions yet | INR 0.00 | - |")
    lines.append("")

    lines.append(f"## {transaction_section + 1}. Benefit Utilization and Recommendation")
    if summary.get("shared_cap"):
        shared = summary["shared_cap"]
        lines.extend([
            f"- Shared 10% cashback cap: {format_money(shared['earned'])} of {format_money(shared['cap'])}; {format_money(shared['remaining'])} remaining",
            f"- Policy version: {summary['policy']['version']} (effective {summary['policy']['effective_from']}; reviewed {summary['policy'].get('reviewed_at') or 'Pending'})",
            "",
        ])
    lines.extend([
        "| Benefit | Spend | Earned/Value | Cap/Target | Remaining | Transactions |",
        "| :--- | ---: | ---: | :--- | :--- | :---: |",
    ])
    if summary["benefits"]:
        for benefit in summary["benefits"].values():
            if benefit.get("cap_group_id"):
                cap = f"Shared {format_money(summary['shared_cap']['cap'])}"
                remaining = "See shared cap"
            else:
                cap = format_money(benefit.get("cap")) if benefit.get("cap") is not None else "Uncapped"
                remaining = format_money(benefit.get("remaining_cap")) if benefit.get("remaining_cap") is not None else "-"
            lines.append(
                f"| {benefit['name']} | {format_money(benefit['spend'])} | {format_money(benefit['earned'])} | {cap} | {remaining} | {benefit['count']} |"
            )
    else:
        lines.append("| Variant-gated rewards | INR 0.00 | Pending | Pending | Pending | 0 |")
    if summary.get("reward_points"):
        points = summary["reward_points"]
        if points.get("lifetime_points"):
            lifetime = points["lifetime_points"]
            cap = points["accelerated_cap"]
            lines.extend([
                "", "Reward points summary:",
                f"- Lifetime points: {lifetime['total']:,} ({lifetime['base']:,} base + {lifetime['accelerated']:,} accelerated + {lifetime['bonus']:,} bonus; {lifetime['evidence_status']} evidence)",
                f"- Accelerated SmartBuy RP this month: {cap['earned']:,} of {cap['cap']:,}; {cap['remaining']:,} remaining ({cap['remaining_percent']:.1f}%), resets {cap['reset_date']}",
            ])
        else:
            lines.extend([
                "",
                "Reward redemption readiness:",
                f"- Base points from tracked cycle spend: {points['base_points']}",
                f"- SmartBuy travel value estimate: {format_money(points['smartbuy_value'])}",
                f"- Airmiles value estimate: {points['airmile_value']} miles-equivalent",
                f"- Voucher value estimate: {format_money(points['voucher_value'])}",
                f"- Cashback value estimate: {format_money(points['cashback_value'])}",
            ])
    lines.extend(["", summary["recommendation_note"], ""])
    if summary.get("unclassified"):
        count = int(summary["unclassified"]["transactions"])
        noun = "transaction" if count == 1 else "transactions"
        lines.append(
            f"- Needs MCC evidence: {format_money(summary['unclassified']['spend'])} across {count} {noun}"
        )
    fuel = (summary.get("limited_offers") or {}).get("fuel")
    if fuel:
        lines.extend([
            "",
            "### Contactless fuel offer",
            render_milestone(
                current=fuel["progress"], target=fuel["target"], format_value=format_money,
                evidence_state="verified" if fuel["evidence_status"] == "confirmed" else "pending",
                period=f"{fuel['period_start']} to {fuel['deadline']}",
                deadline=parse_date(fuel["deadline"]), as_of=as_of,
                supporting_lines=(
                    f"Potential reward: {format_money(fuel['reward'])}",
                    "Official source conflict: product-page annual wording differs from the linked quarterly offer terms."
                    if fuel["source_conflict"] else "Source terms aligned.",
                ),
            ),
        ])
    lounges = (summary.get("entitlements") or {}).get("lounges", [])
    if lounges:
        lines.extend(["", "### Lounge entitlements"])
        for lounge in lounges:
            usage = "Usage not confirmed" if lounge["used"] is None else f"{lounge['used']} used"
            availability = "available" if lounge["available"] else "not currently available"
            lines.append(
                f"- {lounge['label']}: {lounge['allowance']} visit; {usage}; {availability}; "
                f"{lounge['period_start']} to {lounge['period_end']}"
            )
    if config.get("perks"):
        lines.extend(["", "### Visa Infinite and Live+ perks"])
        for perk in config["perks"]:
            lines.append(f"- [{perk['label']}]({perk['url']}): {perk['detail']}")
    lines.append("")

    lines.extend([f"## {transaction_section + 2}. Source Notes", render_sources(config), ""])
    return "\n".join(lines)


def build_dashboard_summary(
    config: dict[str, Any], summary: dict[str, Any], metadata: dict[str, Any], alert_count: int
) -> dict[str, Any]:
    benefit_rows = []
    calculated = summary["benefits"]
    if summary.get("policy"):
        for name, row in calculated.items():
            benefit_rows.append({
                "name": name, "rate": float(row.get("rate", 0)), "spend": float(row.get("spend", 0)),
                "earned": float(row.get("earned", 0)), "cap": None, "remaining": None,
                "provisional": row.get("evidence_status") == "estimated",
                "cap_group_id": row.get("cap_group_id"),
                "evidence_status": row.get("evidence_status", "unavailable"),
            })
    else:
        for rule in config.get("benefit_rules", []):
            name = rule.get("name", "Eligible Spends")
            row = calculated.get(name, {})
            cap = rule.get("monthly_cap")
            benefit_rows.append({
                "name": name, "spend": float(row.get("spend", 0)), "earned": float(row.get("earned", 0)),
                "cap": None if cap is None else float(cap),
                "remaining": None if cap is None else float(row.get("remaining_cap", cap)),
                "provisional": bool(row.get("provisional", rule.get("provisional", False))),
            })
        for name, row in calculated.items():
            if name not in {item["name"] for item in benefit_rows}:
                benefit_rows.append({"name": name, "spend": row["spend"], "earned": row["earned"],
                                     "cap": row["cap"], "remaining": row["remaining_cap"],
                                     "provisional": bool(row.get("provisional", False))})
    annual_fee = dict(summary["annual_fee"])
    annual_fee["evidence_state"] = config.get("annual_fee", {}).get("evidence_state", "verified")
    annual_fee["evidence_source"] = config.get("annual_fee", {}).get("evidence_source")
    welcome = dict(summary["welcome"])
    welcome_config = config.get("welcome", {})
    welcome.update({
        "activation_proxy_date": welcome_config.get("activation_proxy_date"),
        "activation_proxy_source": welcome_config.get("activation_proxy_source"),
        "evidence_state": welcome_config.get("evidence_state", "verified"),
        "memberships": welcome_config.get("memberships", []),
    })
    cycle_config = config.get("cycle", {})
    cycle_payload = {
        "start": summary["cycle_start"],
        "end": summary["cycle_end"],
        "spend": summary["total_spend"],
    }
    for source_key in ("evidence_status", "source", "statement_date"):
        if cycle_config.get(source_key):
            cycle_payload[source_key] = cycle_config[source_key]
    payload = {
        "schema_version": 2 if summary.get("policy") else 1,
        "card": {"name": summary["card_name"], "ending": summary["card_ending"]},
        "cycle": cycle_payload,
        "benefits": benefit_rows, "annual_fee": annual_fee, "welcome": welcome,
        "rewards": summary.get("reward_points"),
        "quarterly_bonus": summary.get("quarterly_bonus"),
        "evergreen_benefits": config.get("benefits", []),
        "evidence": {"variant_status": summary["variant_status"]},
        "provisional": any(item["provisional"] for item in benefit_rows),
        "generated_at": datetime.now().astimezone().isoformat(), "run_id": metadata.get("run_id"),
        "alert_count": alert_count,
    }
    if summary.get("policy"):
        payload.update({
            "policy": summary["policy"],
            "shared_cap": summary["shared_cap"],
            "period_totals": summary["period_totals"],
            "unclassified": summary["unclassified"],
            "limited_offers": summary["limited_offers"],
            "entitlements": summary["entitlements"],
            "perks": config.get("perks", []),
        })
    return payload


def validate_dashboard_payload(
    payload: dict[str, Any], metadata: dict[str, Any], validation: dict[str, Any], cache_count: int
) -> None:
    if not validation.get("ok"):
        raise ValueError("dashboard payload requires a successful validation_report.json")
    run_ids = (payload.get("run_id"), metadata.get("run_id"), validation.get("run_id"))
    if not run_ids[0] or len(set(run_ids)) != 1:
        raise ValueError("dashboard payload run_id does not match sync metadata and validation_report")
    counts = (
        payload.get("alert_count"), cache_count, metadata.get("alert_count"),
        metadata.get("unique_alert_count"), validation.get("alert_count"),
    )
    if any(isinstance(value, bool) or not isinstance(value, int) for value in counts) or len(set(counts)) != 1:
        raise ValueError("dashboard payload alert_count does not match cache, sync metadata, and validation_report")
    if payload.get("schema_version") == 2:
        policy = payload.get("policy") or {}
        shared_cap = payload.get("shared_cap") or {}
        period_totals = payload.get("period_totals") or {}
        if not policy.get("version") or not policy.get("effective_from") or not policy.get("reviewed_at"):
            raise ValueError("dashboard payload HSBC policy evidence is incomplete")
        cap = shared_cap.get("cap")
        earned = shared_cap.get("earned")
        remaining = shared_cap.get("remaining")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (cap, earned, remaining)):
            raise ValueError("dashboard payload HSBC shared cap is malformed")
        if cap <= 0 or round(float(earned) + float(remaining), 2) != round(float(cap), 2):
            raise ValueError("dashboard payload HSBC shared cap does not reconcile")
        current_spend = (period_totals.get("spend") or {}).get("current_cycle")
        if not isinstance(current_spend, (int, float)) or round(float(current_spend), 2) != round(float(payload["cycle"]["spend"]), 2):
            raise ValueError("dashboard payload HSBC current-cycle spend does not reconcile")


def write_report(card_dir: Path | str, as_of: date | None = None) -> Path:
    card_dir = Path(card_dir)
    as_of = as_of or date.today()
    config = load_config(card_dir)
    alerts = load_alerts(card_dir)
    summary = calculate_benefits(config, alerts, as_of=as_of)
    metadata = load_json(card_dir / "sync_metadata.json", {})
    validation = load_json(card_dir / "validation_report.json", {})
    alert_count = len(alerts)
    dashboard = build_dashboard_summary(config, summary, metadata, alert_count)
    if any(name in str(config.get("card_name", "")).upper() for name in ("HSBC LIVE+", "HDFC DINERS BLACK METAL")):
        validate_dashboard_payload(dashboard, metadata, validation, alert_count)
    report = build_report(card_dir, as_of=as_of)
    path = card_dir / "benefit_tracker_report.md"
    path.write_text(report, encoding="utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=".dashboard_summary.", suffix=".tmp", dir=card_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(dashboard, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, card_dir / "dashboard_summary.json")
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return path


def build_statements_data(card_dir: Path | str) -> dict[str, Any]:
    card_dir = Path(card_dir)
    alerts = load_alerts(card_dir)
    payload = {
        "statements": [],
        "transactions": alerts,
        "notes": ["Statement PDF parsing is ready; current data is sourced from Gmail alerts until statement PDFs are available."],
    }
    write_json(card_dir / "statements_data.json", payload)
    return payload


def validate_card_dir(card_dir: Path | str) -> dict[str, Any]:
    card_dir = Path(card_dir)
    config = load_config(card_dir)
    alerts = load_alerts(card_dir)
    warnings = []
    failures = []
    if not config:
        failures.append("benefits_config.json is missing or empty")
    if not config.get("sources"):
        warnings.append("No official source URLs configured")
    if config.get("variant_status") != "confirmed":
        warnings.append("Card variant is pending; reward recommendations remain disabled")
    if not alerts:
        warnings.append("No Gmail transaction alerts are cached yet")
    freshness = card_freshness.validate_freshness(
        card_dir,
        card_name=config.get("card_name", "card"),
        env_prefix=str(config.get("card_name", "CARD")).upper().replace(" ", "_").replace("+", "PLUS"),
        require_metadata=True,
        require_connector_evidence=False,
    )
    warnings.extend(freshness["warnings"])
    failures.extend(freshness["failures"])
    metadata = load_json(card_dir / "sync_metadata.json", {})
    try:
        build_report(card_dir)
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        failures.append(f"Report rendering failed: {exc}")
    result = {
        "ok": not failures,
        "warnings": warnings,
        "failures": failures,
        "freshness": freshness,
        "run_id": metadata.get("run_id"),
        "alert_count": len(alerts),
    }
    write_json(card_dir / "validation_report.json", result)
    return result


def sync_from_step_logs(card_dir: Path | str) -> dict[str, Any]:
    card_dir = Path(card_dir)
    config = load_config(card_dir)
    alerts = load_alerts(card_dir)
    write_json(card_dir / "gmail_alerts.json", alerts)
    metadata = card_freshness.write_sync_metadata(
        card_dir,
        card_name=config.get("card_name", ""),
        card_ending=config.get("card_ending", ""),
        source="cached-alerts",
        query=config.get("gmail_query", ""),
        alerts=alerts,
        previous_count=len(alerts),
        new_count=0,
        skipped_duplicate_count=0,
        warnings=["This sync reused cached alerts only; run a live Gmail connector refresh for current totals."],
    )
    return {
        "ok": True,
        "alerts": len(alerts),
        "metadata": metadata,
        "message": "Using cached Gmail alerts already present on disk; validation will require a live sync before totals are trusted.",
    }


def print_validation(result: dict[str, Any]) -> int:
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1
