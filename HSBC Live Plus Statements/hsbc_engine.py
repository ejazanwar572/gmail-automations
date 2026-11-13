#!/usr/bin/env python3
"""
HSBC Live+ Credit Card Cashback & Analytics Engine.
Calculates 10% accelerated cashback, ₹1,200 monthly cap utilization,
billing cycle tracking (14th to 13th), spend headroom, fee waiver progress,
and categorizes transactions using the MCC Registry and official whitelist.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ENGINE_DIR = Path(__file__).resolve().parent


def parse_date(d_str: Any) -> Optional[date]:
    if not d_str:
        return None
    try:
        return datetime.fromisoformat(str(d_str)[:10]).date()
    except Exception:
        return None


def get_billing_cycle(reference_date: date, cycle_day: int = 13) -> Tuple[date, date, int]:
    """
    Returns (cycle_start, cycle_end, days_remaining).
    HSBC Live+ cycle runs from (cycle_day + 1) of Month A to cycle_day of Month B.
    E.g. If reference_date is 12 Sep 2026 and cycle_day is 13:
      cycle_start = 14 Aug 2026
      cycle_end = 13 Sep 2026
      days_remaining = (13 Sep - 12 Sep) = 1 day
    """
    if reference_date.day <= cycle_day:
        # Currently in cycle ending this month
        year = reference_date.year
        month = reference_date.month
        cycle_end = date(year, month, cycle_day)
        # cycle_start is previous month's cycle_day + 1
        first_of_month = date(year, month, 1)
        last_of_prev_month = first_of_month - timedelta(days=1)
        cycle_start = date(last_of_prev_month.year, last_of_prev_month.month, cycle_day + 1)
    else:
        # Currently in cycle ending next month
        year = reference_date.year
        month = reference_date.month
        cycle_start = date(year, month, cycle_day + 1)
        # Next month cycle_end
        if month == 12:
            cycle_end = date(year + 1, 1, cycle_day)
        else:
            cycle_end = date(year, month + 1, cycle_day)

    days_remaining = max(0, (cycle_end - reference_date).days)
    return cycle_start, cycle_end, days_remaining


def match_mcc_and_category(
    merchant_name: str,
    registry: dict,
    policy: dict,
    tx_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Resolves merchant MCC, eligible cashback rate, category, and audit evidence status.
    """
    m_clean = merchant_name.strip().upper()
    merchants_map = registry.get("merchants", {})

    matched_entry = None
    # 1. Exact or prefix match in community registry
    for pattern, info in merchants_map.items():
        if pattern in m_clean or m_clean in pattern:
            matched_entry = info
            break

    accelerated_rate = float(policy.get("accelerated_rate", 0.10))
    standard_rate = float(policy.get("standard_rate", 0.015))

    if matched_entry:
        mcc = matched_entry.get("mcc")
        cat = matched_entry.get("category", "General Retail")
        
        # Check temporary promo expiry (e.g. Myntra until 31 Oct 2026)
        through = parse_date(matched_entry.get("through"))
        if through and tx_date and tx_date > through:
            return {
                "mcc": mcc,
                "category": cat,
                "rate": standard_rate,
                "rate_pct": f"{standard_rate * 100:.1f}%",
                "is_accelerated": False,
                "evidence": "confirmed",
                "note": matched_entry.get("note", "Standard rate applied post offer"),
            }

        is_accel = matched_entry.get("eligible_10_percent", False)
        rate = accelerated_rate if is_accel else standard_rate
        return {
            "mcc": mcc,
            "category": cat,
            "rate": rate,
            "rate_pct": f"{rate * 100:.1f}%",
            "is_accelerated": is_accel,
            "evidence": "confirmed" if "Estimated" not in matched_entry.get("source", "") else "estimated",
            "source": matched_entry.get("source", "Community Registry"),
        }

    # 2. Keyword fallback with 'estimated' status
    dining_keywords = ["ZOMATO", "SWIGGY", "RESTAURANT", "DINING", "FOOD", "CAFE", "PIZZA", "BURGER", "BAKERY"]
    grocery_keywords = ["BLINK", "ZEPTO", "BIGBASKET", "GROCERY", "SUPERMARKET", "MART", "INSTAMART"]
    utility_keywords = ["ELECTRICITY", "BESCOM", "TNEB", "AIRTEL", "JIO", "VODAFONE", "TELECOM", "UTILITY"]

    if any(k in m_clean for k in dining_keywords):
        return {
            "mcc": "5812",
            "category": "Dining and food delivery",
            "rate": accelerated_rate,
            "rate_pct": f"{accelerated_rate * 100:.1f}%",
            "is_accelerated": True,
            "evidence": "estimated",
            "source": "Keyword Inference (Pending Statement)",
        }
    if any(k in m_clean for k in grocery_keywords):
        return {
            "mcc": "5411",
            "category": "Grocery",
            "rate": accelerated_rate,
            "rate_pct": f"{accelerated_rate * 100:.1f}%",
            "is_accelerated": True,
            "evidence": "estimated",
            "source": "Keyword Inference (Pending Statement)",
        }
    if any(k in m_clean for k in utility_keywords):
        return {
            "mcc": "4900",
            "category": "Utilities",
            "rate": accelerated_rate,
            "rate_pct": f"{accelerated_rate * 100:.1f}%",
            "is_accelerated": True,
            "evidence": "estimated",
            "source": "Keyword Inference (Pending Statement)",
        }

    # 3. Default standard eligible spend
    return {
        "mcc": "Retail",
        "category": "Other Eligible Spends",
        "rate": standard_rate,
        "rate_pct": f"{standard_rate * 100:.1f}%",
        "is_accelerated": False,
        "evidence": "standard",
        "source": "Base Cashback",
    }


def compute_hsbc_dashboard_data(card_dir: Path, today: Optional[date] = None) -> Dict[str, Any]:
    """
    Computes all summary metrics for the HSBC Live+ dashboard.
    """
    if today is None:
        today = date.today()

    config_file = card_dir / "benefits_config.json"
    alerts_file = card_dir / "gmail_alerts.json"
    registry_file = card_dir / "mcc_registry.json"
    sync_meta_file = card_dir / "sync_metadata.json"

    config = json.loads(config_file.read_text()) if config_file.exists() else {}
    alerts = json.loads(alerts_file.read_text()) if alerts_file.exists() else []
    registry = json.loads(registry_file.read_text()) if registry_file.exists() else {"merchants": {}}
    sync_meta = json.loads(sync_meta_file.read_text()) if sync_meta_file.exists() else {}

    policy = config.get("cashback_policy", {})
    monthly_cap_amount = float(policy.get("accelerated_cap", 1200))
    accelerated_rate = float(policy.get("accelerated_rate", 0.10))
    max_accelerated_spend = monthly_cap_amount / accelerated_rate  # Exactly ₹12,000

    cycle_start, cycle_end, days_remaining = get_billing_cycle(today, cycle_day=13)

    # Filter transactions
    classified_txns = []
    cycle_txns = []
    cycle_accelerated_spend = 0.0
    cycle_standard_spend = 0.0
    cycle_accelerated_cb = 0.0
    cycle_standard_cb = 0.0
    cycle_confirmed_cb = 0.0
    cycle_estimated_cb = 0.0

    lifetime_spend = 0.0
    lifetime_cb = 0.0

    # Sort alerts descending
    sorted_alerts = sorted(alerts, key=lambda x: x.get("date", ""), reverse=True)

    for item in sorted_alerts:
        amt = float(item.get("amount", 0.0))
        tx_d = parse_date(item.get("date"))
        merchant = item.get("merchant", "Unknown")

        # Ignore authorization test tokens (e.g. ₹2 lounge auth)
        is_token = (amt <= 2.0 and "LOUNGE" in merchant.upper()) or (amt <= 2.0 and "BLR DOM" in merchant.upper())

        mcc_res = match_mcc_and_category(merchant, registry, policy, tx_d)

        # Calculate cashback
        if is_token:
            earned_cb = 0.0
            category_tag = "Lounge Auth (Token)"
            rate_disp = "0%"
        elif mcc_res["is_accelerated"]:
            earned_cb = round(amt * accelerated_rate, 2)
            category_tag = mcc_res["category"]
            rate_disp = "10.0%"
        else:
            earned_cb = round(amt * float(mcc_res["rate"]), 2)
            category_tag = mcc_res["category"]
            rate_disp = mcc_res["rate_pct"]

        classified_entry = {
            "date": item.get("date"),
            "merchant": merchant,
            "amount": amt,
            "category": category_tag,
            "mcc": mcc_res.get("mcc", "-"),
            "rate": rate_disp,
            "is_accelerated": mcc_res.get("is_accelerated", False),
            "cashback_earned": earned_cb,
            "evidence": mcc_res.get("evidence", "standard"),
            "source": mcc_res.get("source", ""),
            "is_token": is_token,
        }
        classified_txns.append(classified_entry)

        if not is_token:
            lifetime_spend += amt
            lifetime_cb += earned_cb

        # Check if in current billing cycle
        if tx_d and cycle_start <= tx_d <= cycle_end and not is_token:
            cycle_txns.append(classified_entry)
            if mcc_res["is_accelerated"]:
                cycle_accelerated_spend += amt
                cycle_accelerated_cb += earned_cb
                if classified_entry["evidence"] == "confirmed":
                    cycle_confirmed_cb += earned_cb
                else:
                    cycle_estimated_cb += earned_cb
            else:
                cycle_standard_spend += amt
                cycle_standard_cb += earned_cb

    # Apply monthly cap: max ₹1,200
    capped_cycle_accelerated_cb = min(monthly_cap_amount, cycle_accelerated_cb)
    total_cycle_cb = capped_cycle_accelerated_cb + cycle_standard_cb
    remaining_cb = max(0.0, monthly_cap_amount - capped_cycle_accelerated_cb)
    remaining_accelerated_spend = max(0.0, max_accelerated_spend - cycle_accelerated_spend)
    cap_percent_used = round(min(100.0, (capped_cycle_accelerated_cb / monthly_cap_amount) * 100), 1)

    effective_reward_rate = (lifetime_cb / lifetime_spend * 100) if lifetime_spend > 0 else 0.0

    # Fee waiver tracker (₹2,00,000 annual spend)
    fee_config = config.get("annual_fee", {})
    fee_waiver_target = float(fee_config.get("waiver_spend", 200000))
    fee_spend_remaining = max(0.0, fee_waiver_target - lifetime_spend)
    fee_percent = round(min(100.0, (lifetime_spend / fee_waiver_target) * 100), 1)
    period_end = parse_date(fee_config.get("period_end")) or (today + timedelta(days=289))
    days_left_fee = max(0, (period_end - today).days)
    run_rate_needed = round(fee_spend_remaining / days_left_fee, 2) if days_left_fee > 0 else 0.0

    # Welcome offer tracker (₹20,000 spend in first 30 days)
    welcome_spend = 20796.46
    welcome_target = 20000.0
    welcome_unlocked = welcome_spend >= welcome_target

    return {
        "card_name": "HSBC Live+ Credit Card",
        "card_ending": "8690",
        "cycle": {
            "start": cycle_start.isoformat(),
            "end": cycle_end.isoformat(),
            "label": f"Current Cycle ({cycle_start.strftime('%d %b')} – {cycle_end.strftime('%d %b')})",
            "days_remaining": days_remaining,
            "reset_str": "Resets Today" if days_remaining == 0 else ("Resets Tomorrow" if days_remaining == 1 else f"Resets in {days_remaining} days"),
        },
        "cashback_cap": {
            "cap_limit": monthly_cap_amount,
            "earned": capped_cycle_accelerated_cb,
            "confirmed_cb": round(cycle_confirmed_cb, 2),
            "estimated_cb": round(cycle_estimated_cb, 2),
            "total_cycle_cb": total_cycle_cb,
            "remaining_cb": remaining_cb,
            "percent_used": cap_percent_used,
            "accelerated_spend": cycle_accelerated_spend,
            "max_accelerated_spend": max_accelerated_spend,
            "remaining_accelerated_spend": remaining_accelerated_spend,
        },
        "portfolio": {
            "lifetime_cashback": lifetime_cb,
            "lifetime_spend": lifetime_spend,
            "effective_reward_rate": round(effective_reward_rate, 2),
        },
        "fee_waiver": {
            "annual_fee": 999,
            "target": fee_waiver_target,
            "spent": lifetime_spend,
            "remaining": fee_spend_remaining,
            "percent": fee_percent,
            "days_left": days_left_fee,
            "run_rate_needed": run_rate_needed,
        },
        "welcome": {
            "spent": welcome_spend,
            "target": welcome_target,
            "unlocked": welcome_unlocked,
            "reward": 1000,
        },
        "lounge": {
            "domestic_h2": "1 Visit Left",
            "international": "1 Visit Left",
            "esim": "Active",
        },
        "transactions": {
            "current_cycle": cycle_txns,
            "all": classified_txns,
        },
        "sync_metadata": {
            "last_synced": sync_meta.get("synced_at", datetime.now().isoformat()),
            "alert_count": len(alerts),
        },
    }


def trigger_live_sync(card_dir: Path = ENGINE_DIR) -> dict:
    """Executes HSBC-specific sync_alerts to fetch new Gmail alerts in-process with isolated module loading."""
    import importlib.util
    sync_script = Path(card_dir) / "sync_alerts.py"
    if not sync_script.exists():
        raise FileNotFoundError(f"sync script not found at {sync_script}")
    module_name = "hsbc_live_plus_sync_alerts"
    spec = importlib.util.spec_from_file_location(module_name, sync_script)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.run(Path(card_dir))
        alerts_file = Path(card_dir) / "gmail_alerts.json"
        count = len(json.loads(alerts_file.read_text())) if alerts_file.exists() else 0
        return {"status": "ok", "alert_count": count, "metadata": result}
    raise RuntimeError(f"could not load sync script at {sync_script}")


def build_statements_data(card_dir: Path | str = ENGINE_DIR) -> dict[str, Any]:
    """Build statement data from cached Gmail alerts."""
    card_dir = Path(card_dir)
    alerts_file = card_dir / "gmail_alerts.json"
    alerts = json.loads(alerts_file.read_text(encoding="utf-8")) if alerts_file.exists() else []
    payload = {
        "statements": [],
        "transactions": alerts,
        "notes": ["Statement PDF parsing is ready; current data is sourced from Gmail alerts until statement PDFs are available."],
    }
    with open(card_dir / "statements_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return payload


def validate_card_dir(card_dir: Path | str = ENGINE_DIR) -> dict[str, Any]:
    """Validate HSBC card directory configuration and calculation health."""
    card_dir = Path(card_dir)
    config_file = card_dir / "benefits_config.json"
    alerts_file = card_dir / "gmail_alerts.json"
    metadata_file = card_dir / "sync_metadata.json"

    config = json.loads(config_file.read_text(encoding="utf-8")) if config_file.exists() else {}
    alerts = json.loads(alerts_file.read_text(encoding="utf-8")) if alerts_file.exists() else []
    metadata = json.loads(metadata_file.read_text(encoding="utf-8")) if metadata_file.exists() else {}

    warnings = []
    failures = []
    if not config:
        failures.append("benefits_config.json is missing or empty")
    if not alerts:
        warnings.append("No Gmail transaction alerts are cached yet")

    if not metadata:
        warnings.append("sync_metadata.json is missing; run sync_alerts")
    else:
        synced_at_str = metadata.get("synced_at")
        if synced_at_str:
            try:
                synced_at = datetime.fromisoformat(synced_at_str.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - synced_at).total_seconds() / 3600
                if age_hours > 36:
                    warnings.append(f"sync_metadata is {age_hours:.1f} hours old (> 36 hours)")
            except Exception:
                pass

    try:
        compute_hsbc_dashboard_data(card_dir)
    except Exception as exc:
        failures.append(f"Dashboard data computation failed: {exc}")

    result = {
        "ok": not failures,
        "warnings": warnings,
        "failures": failures,
        "run_id": metadata.get("run_id"),
        "alert_count": len(alerts),
    }
    with open(card_dir / "validation_report.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    return result


def print_validation(result: dict[str, Any]) -> int:
    """Print validation report as JSON and return exit code."""
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


def write_report(card_dir: Path | str = ENGINE_DIR, as_of: date | None = None) -> Path:
    """Generate benefit tracker report and update dashboard_summary.json atomically."""
    card_dir = Path(card_dir)
    as_of = as_of or date.today()
    data = compute_hsbc_dashboard_data(card_dir, today=as_of)
    metadata_file = card_dir / "sync_metadata.json"
    metadata = json.loads(metadata_file.read_text(encoding="utf-8")) if metadata_file.exists() else {}

    cycle_spend = sum(t.get("amount", 0.0) for t in data["transactions"].get("current_cycle", []))

    dashboard = {
        "schema_version": 2,
        "card": {"name": data["card_name"], "ending": data["card_ending"]},
        "cycle": {
            "start": str(data["cycle"]["start"]),
            "end": str(data["cycle"]["end"]),
            "spend": cycle_spend,
            "days_remaining": data["cycle"]["days_remaining"],
        },
        "annual_fee": {
            "amount": data["fee_waiver"]["annual_fee"],
            "waiver_spend": data["fee_waiver"]["target"],
            "progress": data["fee_waiver"]["spent"],
            "remaining": data["fee_waiver"]["remaining"],
            "days_left": data["fee_waiver"]["days_left"],
        },
        "welcome": {
            "target": data["welcome"]["target"],
            "spend": data["welcome"]["spent"],
            "met": data["welcome"]["unlocked"],
            "reward": data["welcome"]["reward"],
        },
        "shared_cap": {
            "cap": data["cashback_cap"]["cap_limit"],
            "earned": data["cashback_cap"]["earned"],
            "remaining": data["cashback_cap"]["remaining_cb"],
        },
        "period_totals": {
            "spend": {"current_cycle": cycle_spend, "lifetime": data["portfolio"]["lifetime_spend"]},
            "cashback": {"current_cycle": data["cashback_cap"]["total_cycle_cb"], "lifetime": data["portfolio"]["lifetime_cashback"]},
        },
        "generated_at": datetime.now().astimezone().isoformat(),
        "run_id": metadata.get("run_id"),
        "alert_count": len(data["transactions"].get("all", [])),
    }

    import tempfile
    fd, temp_name = tempfile.mkstemp(prefix=".dashboard_summary.", suffix=".tmp", dir=card_dir)
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            json.dump(dashboard, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, card_dir / "dashboard_summary.json")
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

    report_lines = [
        f"# {data['card_name']}: Benefit Tracker Report",
        "",
        "## 1. Executive Summary",
        f"- Card ending: {data['card_ending']}",
        f"- Current cycle: {data['cycle']['start']} to {data['cycle']['end']}",
        f"- Current cycle tracked spend: INR {cycle_spend:,.2f}",
        f"- Current cycle cashback earned: INR {data['cashback_cap']['total_cycle_cb']:,.2f}",
        f"- Data freshness: {metadata.get('alert_count', 0)} alerts; cached total INR {metadata.get('cached_total', 0.0):,.2f}.",
        "",
        "## 2. Fee and Waiver Tracker",
        f"- Progress: INR {data['fee_waiver']['spent']:,.2f} of INR {data['fee_waiver']['target']:,.2f} ({data['fee_waiver']['percent']}%)",
        f"- Days left: {data['fee_waiver']['days_left']}",
        f"- Status: {'Met' if data['fee_waiver']['remaining'] <= 0 else 'In progress'}",
        "",
        "## 3. Welcome Benefit Tracker",
        f"- Progress: INR {data['welcome']['spent']:,.2f} of INR {data['welcome']['target']:,.2f}",
        f"- Status: {'Met' if data['welcome']['unlocked'] else 'In progress'}",
        "",
        "## 4. Shared Cashback Cap (10% Dining, Food Delivery, Grocery)",
        f"- Cap: INR {data['cashback_cap']['cap_limit']:,.2f} per billing cycle",
        f"- Earned: INR {data['cashback_cap']['earned']:,.2f}",
        f"- Remaining: INR {data['cashback_cap']['remaining_cb']:,.2f}",
        "",
    ]
    report_path = card_dir / "benefit_tracker_report.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return report_path


def run_card_pipeline(
    card_dir: Path | str = ENGINE_DIR,
    sync_source: str = "gmail-api",
) -> dict[str, Any]:
    """Execute complete HSBC workflow in-process without intermediate subprocess leakage."""
    card_dir = Path(card_dir)
    results: dict[str, Any] = {"ok": True, "steps": {}}

    # 1. Alert Sync
    if sync_source == "gmail-api":
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("hsbc_sync_alerts", card_dir / "sync_alerts.py")
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                sync_res = mod.run(card_dir)
                results["steps"]["sync_alerts"] = {"ok": True, "count": sync_res.get("parsed_count", 0)}
        except Exception as exc:
            results["steps"]["sync_alerts"] = {"ok": False, "error": str(exc)}
            results["ok"] = False
            return results
    elif sync_source == "mcp-step-logs":
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("hsbc_sync_mcp", card_dir / "sync_gmail_mcp.py")
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "main"):
                    mod.main()
                results["steps"]["sync_mcp"] = {"ok": True}
        except Exception as exc:
            results["steps"]["sync_mcp"] = {"ok": False, "error": str(exc)}
            results["ok"] = False
            return results

    # 2. Build Statements Data
    try:
        build_statements_data(card_dir)
        results["steps"]["parse_statements"] = {"ok": True}
    except Exception as exc:
        results["steps"]["parse_statements"] = {"ok": False, "error": str(exc)}
        results["ok"] = False
        return results

    # 3. Validate
    val_res = validate_card_dir(card_dir)
    results["steps"]["validate"] = val_res
    if not val_res.get("ok"):
        results["ok"] = False
        return results

    # 4. Update Report
    rep_path = write_report(card_dir)
    results["steps"]["update_report"] = {"ok": True, "path": str(rep_path)}
    return results



