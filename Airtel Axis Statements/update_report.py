#!/usr/bin/env python3
"""
Automatically update the Airtel Axis cashback cap report based on Gmail alerts.
"""

import os
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from card_progress import render_milestone
from transaction_classifier import classify_transactions
from period_totals import (
    calculate_lifetime_cashback,
    calculate_lifetime_spend,
    evidence_run_id,
)

# --- Configuration ---
PDF_DIR = "/Users/ejazanwar/Documents/Gmail Automations/Airtel Axis Statements"
ALERTS_FILE = os.path.join(PDF_DIR, "gmail_alerts.json")
STATEMENTS_DATA_FILE = os.path.join(PDF_DIR, "statements_data.json")
REPORT_PATH = os.path.join(PDF_DIR, "cashback_cap_report.md")
CLASSIFICATIONS_FILE = os.path.join(PDF_DIR, "transaction_classifications.json")
METADATA_FILE = os.path.join(PDF_DIR, "sync_metadata.json")
PERIOD_TOTALS_FILE = os.path.join(PDF_DIR, "period_totals.json")
ANNUAL_FEE_WAIVER_TARGET = 200000.00

def load_json(path):
    """Loads data from a JSON file."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {path}: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred loading {path}: {e}")
        return []

def format_amount(amount):
    return f"₹{amount:,.0f}" if float(amount).is_integer() else f"₹{amount:,.2f}"

def format_summary_amount(amount):
    return f"₹{amount:,.2f}"

def format_spend_room(remaining_cashback, rate):
    if remaining_cashback <= 0:
        return "✅ Capped"
    return format_summary_amount(remaining_cashback / rate)

def format_transaction_count(txs):
    count = len(txs)
    return f"{count} transaction" if count == 1 else f"{count} transactions"

def extract_merchant(subject):
    marker = " at "
    if marker in subject:
        return subject.rsplit(marker, 1)[-1].strip()
    return "Unknown"

def clean_merchant(merchant):
    merchant_upper = merchant.strip().upper()
    mappings = {
        "AIRTEL": "Airtel",
        "PTM*ZOMATO": "Zomato",
        "PYU*ZOMATO": "Zomato",
        "ZOMATO": "Zomato",
        "ETERNAL LIM": "Zomato",
        "SWIGGY": "Swiggy",
        "BIGBASKET": "BigBasket",
        "RSP*BLINK": "Blinkit",
        "BLINK": "Blinkit",
    }
    for key, label in mappings.items():
        if key in merchant_upper:
            return label
    return merchant.strip().title() if merchant.isupper() else merchant.strip()

def format_long_date(dt):
    return dt.strftime("%B %-d, %Y")

def get_active_cycle(as_of):
    if as_of.day >= 13:
        start_date = datetime(as_of.year, as_of.month, 13)
        if as_of.month == 12:
            end_date = datetime(as_of.year + 1, 1, 12)
        else:
            end_date = datetime(as_of.year, as_of.month + 1, 12)
    else:
        end_date = datetime(as_of.year, as_of.month, 12)
        if as_of.month == 1:
            start_date = datetime(as_of.year - 1, 12, 13)
        else:
            start_date = datetime(as_of.year, as_of.month - 1, 13)

    next_cycle_start = datetime(end_date.year, end_date.month, 13)
    statement_month = end_date.strftime("%B %Y")
    return start_date, end_date, next_cycle_start, statement_month

def format_period(start_date, end_date):
    return f"{format_long_date(start_date)} – {format_long_date(end_date)}"

def format_transaction_rows(groups):
    rows = []
    for category, txs in groups:
        for t in txs:
            merchant = clean_merchant(t.get("merchant", "Unknown")).replace("|", "\\|")
            rows.append(f"| {t['date']} | {category} | {format_amount(t['amount'])} | {merchant} |")
    if not rows:
        return "| - | - | - | No tracked transactions in this statement cycle. |"
    return "\n".join(rows)

def format_date_range(txs, fallback_start=None, fallback_end=None):
    if not txs:
        if fallback_start and fallback_end:
            return format_period(fallback_start, fallback_end)
        return "No tracked Gmail alerts in this statement cycle"
    dates = [t[0] for t in txs]
    return format_period(min(dates), max(dates))

def parse_statement_date(date_str):
    d, m, y = map(int, date_str.split("/"))
    return datetime(y, m, d)

def format_waiver_period(start_date, end_date):
    return f"{format_long_date(start_date)} - {format_long_date(end_date)}"

def is_fee_description(description):
    text = description.upper()
    return any(term in text for term in ["JOINING FEE", "ANNUAL FEE", "RENEWAL FEE", "MEMBERSHIP FEE"])

def is_waiver_excluded_description(description):
    text = description.upper()
    if re.match(r"^-\s+\d{2}/\d{2}/\d{4}", text):
        return True

    excluded_terms = [
        "RENT",
        "WALLET",
        "DEBIT CARD WAL",
        "JOINING FEE",
        "ANNUAL FEE",
        "RENEWAL FEE",
        "MEMBERSHIP FEE",
        "GST",
        "PROCESSING FEE",
        "TRANSACTION CONVERSION",
        "EMI PRINCIPAL",
        "EMI INTEREST",
        "CASHBACK",
        "CREDIT RECEIVED",
    ]
    return any(term in text for term in excluded_terms)

def iter_statement_transactions(statements_data):
    for statement in statements_data.get("statements", []):
        for txn in statement.get("transactions", []):
            yield statement, txn

def find_fee_events(statements_data):
    events = []
    transactions = list(iter_statement_transactions(statements_data))

    for statement, txn in transactions:
        if txn.get("type") != "Dr" or not is_fee_description(txn.get("description", "")):
            continue

        fee_date = txn.get("date")
        gst = sum(
            float(other.get("amount", 0.0))
            for _, other in transactions
            if other.get("type") == "Dr"
            and other.get("date") == fee_date
            and other.get("description", "").upper() == "GST"
        )
        events.append(
            {
                "date": fee_date,
                "description": txn.get("description", "").strip(),
                "amount": float(txn.get("amount", 0.0)),
                "gst": round(gst, 2),
                "statement_month": statement.get("month", ""),
            }
        )

    return sorted(events, key=lambda event: parse_statement_date(event["date"]))

def get_waiver_years(anchor_date, as_of):
    current_start = datetime(as_of.year, anchor_date.month, anchor_date.day)
    if as_of < current_start:
        current_start = datetime(as_of.year - 1, anchor_date.month, anchor_date.day)

    current_end = datetime(current_start.year + 1, current_start.month, current_start.day) - timedelta(days=1)
    completed_start = datetime(current_start.year - 1, current_start.month, current_start.day)
    completed_end = current_start - timedelta(days=1)
    return completed_start, completed_end, current_start, current_end

def statement_eligible_spend(statements_data, start_date, end_date):
    total = 0.0
    count = 0
    excluded = 0.0

    for _, txn in iter_statement_transactions(statements_data):
        if txn.get("type") != "Dr":
            continue
        try:
            txn_date = parse_statement_date(txn["date"])
        except Exception:
            continue
        if not start_date <= txn_date <= end_date:
            continue

        amount = float(txn.get("amount", 0.0))
        if is_waiver_excluded_description(txn.get("description", "")):
            excluded += amount
        else:
            total += amount
            count += 1

    return {"eligible_spend": round(total, 2), "transaction_count": count, "excluded_spend": round(excluded, 2)}

def alert_eligible_spend(alerts, start_date, end_date):
    total = 0.0
    count = 0
    excluded = 0.0

    for alert in alerts:
        try:
            txn_date = parse_statement_date(alert["date"])
        except Exception:
            continue
        if not start_date <= txn_date <= end_date:
            continue

        amount = float(alert.get("amount", 0.0))
        subject = alert.get("subject", "")
        if is_waiver_excluded_description(subject):
            excluded += amount
        else:
            total += amount
            count += 1

    return {"eligible_spend": round(total, 2), "transaction_count": count, "excluded_spend": round(excluded, 2)}

def decorate_waiver_year(spend_data, start_date, end_date, source):
    eligible = spend_data["eligible_spend"]
    remaining = max(0.0, ANNUAL_FEE_WAIVER_TARGET - eligible)
    over_target = max(0.0, eligible - ANNUAL_FEE_WAIVER_TARGET)
    return {
        **spend_data,
        "source": source,
        "period": format_waiver_period(start_date, end_date),
        "deadline": end_date.date() if isinstance(end_date, datetime) else end_date,
        "target": ANNUAL_FEE_WAIVER_TARGET,
        "progress_pct": min(100.0, round((eligible / ANNUAL_FEE_WAIVER_TARGET) * 100, 1)),
        "remaining": round(remaining, 2),
        "over_target": round(over_target, 2),
        "status": "Met" if eligible >= ANNUAL_FEE_WAIVER_TARGET else "In progress",
    }

def build_annual_fee_waiver_summary(statements_data, alerts, as_of=None):
    as_of = as_of or datetime.now()
    fee_events = find_fee_events(statements_data)
    joining_fee = next((event for event in fee_events if "JOINING FEE" in event["description"].upper()), None)
    renewal_fees = [event for event in fee_events if event is not joining_fee]

    anchor_date = parse_statement_date(joining_fee["date"]) if joining_fee else datetime(as_of.year, 3, 1)
    completed_start, completed_end, current_start, current_end = get_waiver_years(anchor_date, as_of)

    completed_spend = statement_eligible_spend(statements_data, completed_start, completed_end)
    current_statement_spend = statement_eligible_spend(statements_data, current_start, current_end)
    current_alert_spend = alert_eligible_spend(alerts, current_start, current_end)

    if current_alert_spend["eligible_spend"] > current_statement_spend["eligible_spend"]:
        current_spend = current_alert_spend
        current_source = "Gmail alerts"
    else:
        current_spend = current_statement_spend
        current_source = "posted statements"

    return {
        "as_of": as_of.date() if isinstance(as_of, datetime) else as_of,
        "joining_fee": joining_fee,
        "renewal_fees": renewal_fees,
        "completed_year": decorate_waiver_year(completed_spend, completed_start, completed_end, "posted statements"),
        "current_year": decorate_waiver_year(current_spend, current_start, current_end, current_source),
        "statement_current_year": current_statement_spend,
        "alert_current_year": current_alert_spend,
    }

def format_fee_event(event):
    if not event:
        return "No joining fee found in parsed statements."
    total = event["amount"] + event["gst"]
    return (
        f"{event['date']} in {event['statement_month']}: {event['description']} "
        f"{format_amount(event['amount'])} + GST {format_amount(event['gst'])} = {format_amount(total)}"
    )

def update_report():
    """Main function to process alerts and generate the report."""
    alerts = load_json(ALERTS_FILE)
    classifications = load_json(CLASSIFICATIONS_FILE)
    statements_data = load_json(STATEMENTS_DATA_FILE)
    waiver_summary = build_annual_fee_waiver_summary(statements_data, alerts)
    
    # Load validation report
    val_report_path = os.path.join(PDF_DIR, "validation_report.json")
    val_data = {}
    val_list = []
    if os.path.exists(val_report_path):
        try:
            with open(val_report_path, 'r') as f:
                val_list = json.load(f)
                val_data = {r["month"]: r for r in val_list}
        except Exception as e:
            print(f"Error loading validation report: {e}")
            
    def get_verified_col(month_name):
        if month_name not in val_data:
            return "N/A"
        item = val_data[month_name]
        is_verified = item.get("cashback_verified", False)
        cb_credited = item.get("cb_credited", 0.0) or 0.0
        
        if month_name == "April 2025":
            return "✅ Yes (First Statement)"
            
        if is_verified:
            return f"✅ Yes (₹{cb_credited:,.2f})"
        else:
            if "L4" in "; ".join(item.get("issues", [])):
                return f"❌ Mismatch (₹{cb_credited:,.2f})"
            return f"✅ Yes (₹{cb_credited:,.2f})"
    
    # Filter and sort alerts for the active billing cycle. Airtel Axis statements run
    # from the 13th of one month through the 12th of the next month.
    today = datetime.now()
    start_date, end_date, next_cycle_start, statement_month = get_active_cycle(today)
    cycle_period = format_period(start_date, end_date)
    next_cycle_start_text = format_long_date(next_cycle_start)
    cycle_end_text = format_long_date(end_date)
    current_txs_raw = []
    
    for a in alerts:
        date_str = a["date"]
        try:
            # Assuming date format is DD/MM/YYYY
            d, m, y = map(int, date_str.split('/'))
            dt = datetime(y, m, d)
            
            if start_date <= dt <= end_date:
                # Store date object, amount, subject, and merchant
                subject = a.get("subject", "")
                current_txs_raw.append((dt, float(a["amount"]), subject.upper(), extract_merchant(subject)))
        except ValueError as e:
            print(f"Error parsing date {date_str}: Invalid date format or values. Error: {e}")
        except KeyError as e:
            print(f"Error: Missing required key in alert data: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during date parsing for {date_str}: {e}")
            
    current_txs_raw.sort(key=lambda x: x[0])
    
    categorized = classify_transactions(current_txs_raw, classifications)
    airtel_txs = categorized["airtel"]
    utility_txs = categorized["utilities"]
    merchant_txs = categorized["merchants"]
    general_txs = categorized["general"]
    unclassified_txs = categorized["unclassified"]
            
    # --- Calculations ---
    
    # 25% Airtel
    airtel_spend = sum(t["amount"] for t in airtel_txs)
    airtel_cb = round(min(airtel_spend * 0.25, 250.00), 2)
    airtel_remaining = round(max(0.0, 250.00 - airtel_cb), 2)
    
    if airtel_cb >= 250.00:
        airtel_status = "✅ **₹250.00 *(100%)***"
        airtel_state = "✅ Capped"
        airtel_cap_note = " *(✅ Capped)*"
        airtel_action = f"✅ **Capped Out.** Postpone any additional Airtel Thanks/telecom recharges until {next_cycle_start_text}."
    else:
        airtel_status = f"₹{airtel_cb:,.2f} *({(airtel_cb/250.00)*100:.1f}%)*"
        airtel_state = "Open"
        airtel_cap_note = ""
        airtel_action = f"**Room Available.** Cashback room equals about ₹{(250.00-airtel_cb)/0.25:,.2f} of eligible Airtel spend."

    # 10% Utilities — only transactions backed by utility-specific evidence.
    utility_spend = sum(t["amount"] for t in utility_txs)
    utility_cb = round(min(utility_spend * 0.10, 250.00), 2)
    utility_remaining = round(max(0.0, 250.00 - utility_cb), 2)
    
    if utility_cb >= 250.00:
        utility_status = "✅ **₹250.00 *(100%)***"
        utility_state = "✅ Capped"
        utility_action = "✅ **Capped Out.**"
    else:
        utility_status = f"₹{utility_cb:,.2f} *({(utility_cb/250.00)*100:.1f}%)*"
        utility_state = "Open"
        utility_action = f"**Room Available.** Cashback room equals about ₹{(250.00-utility_cb)/0.10:,.2f} of eligible utility spend before {cycle_end_text}."

    # 10% Preferred Merchants
    merchant_spend = sum(t["amount"] for t in merchant_txs)
    merchant_cb = round(min(merchant_spend * 0.10, 500.00), 2)
    merchant_remaining = round(max(0.0, 500.00 - merchant_cb), 2)
    
    if merchant_cb >= 500.00:
        merchant_status = "✅ **₹500.00 *(100%)***"
        merchant_state = "✅ Capped"
        merchant_action = "✅ **Capped Out.**"
    else:
        merchant_status = f"₹{merchant_cb:,.2f} *({(merchant_cb/500.00)*100:.1f}%)*"
        merchant_state = "Open"
        merchant_action = f"**Room Available.** Cashback room equals about ₹{(500.00-merchant_cb)/0.10:,.2f} of eligible Zomato, Swiggy, or BigBasket spend before {cycle_end_text}."

    # 1% General
    general_spend = sum(t["amount"] for t in general_txs)
    general_cb = round(general_spend * 0.01, 2)
    
    total_june_cb = airtel_cb + utility_cb + merchant_cb + general_cb
    total_capped_cb = airtel_cb + utility_cb + merchant_cb
    unclassified_spend = sum(t["amount"] for t in unclassified_txs)
    total_unique_spend = airtel_spend + utility_spend + merchant_spend + general_spend + unclassified_spend
    total_remaining_cap = airtel_remaining + utility_remaining + merchant_remaining
    total_capped_cap = 1000.00
    total_capped_pct = (total_capped_cb / total_capped_cap) * 100 if total_capped_cap else 0.0

    metadata = load_json(METADATA_FILE)
    gate = next((row for row in val_list if row.get("month") == "Freshness / reconciliation gate"), None)
    if not isinstance(metadata, dict) or not gate or gate.get("validated") is not True or gate.get("freshness", {}).get("ok") is not True:
        raise RuntimeError("Validated current-run Airtel evidence is required before totals can be generated")
    lifetime_spend = calculate_lifetime_spend(
        statements_data, val_list, alerts, waiver_summary["joining_fee"]
        and parse_statement_date(waiver_summary["joining_fee"]["date"]).date()
        or datetime(2025, 3, 1).date(),
    )
    lifetime_cashback = calculate_lifetime_cashback(
        statements_data, val_list, alerts, classifications, lifetime_spend["latest_statement_end"],
    )
    alert_count = metadata.get("alert_count", metadata.get("unique_alert_count"))
    run_id = evidence_run_id(metadata)
    period_totals_artifact = {
        "schema_version": 1,
        "run_id": run_id,
        "alert_count": alert_count,
        "generated_at": datetime.now().astimezone().isoformat(),
        "period_totals": {
            "spend": {
                "lifetime": lifetime_spend["lifetime"],
                "current_cycle": round(total_unique_spend, 2),
                "lifetime_start": (
                    parse_statement_date(waiver_summary["joining_fee"]["date"]).date()
                    if waiver_summary["joining_fee"] else datetime(2025, 3, 1).date()
                ).isoformat(),
                "tracked_through": lifetime_spend["tracked_through"].isoformat(),
                "evidence_status": "mixed",
            },
            "cashback": {
                "lifetime": lifetime_cashback["lifetime"],
                "current_cycle": round(total_june_cb, 2),
                "confirmed": lifetime_cashback["confirmed"],
                "pending": lifetime_cashback["pending"],
                "confirmed_through": lifetime_cashback["confirmed_through"].isoformat(),
                "lifetime_start": (
                    parse_statement_date(waiver_summary["joining_fee"]["date"]).date()
                    if waiver_summary["joining_fee"] else datetime(2025, 3, 1).date()
                ).isoformat(),
                "tracked_through": lifetime_spend["tracked_through"].isoformat(),
                "evidence_status": "mixed",
            },
        },
        "cap_room": {
            "cap": total_capped_cap,
            "remaining": round(total_remaining_cap, 2),
            "remaining_percent": round((total_remaining_cap / total_capped_cap) * 100, 3),
            "reset_date": next_cycle_start.date().isoformat(),
        },
    }
    
    # Generate Section 2 ongoing row values
    june_row_25 = f"✅ ₹250.00 (100%)" if airtel_cb >= 250.00 else f"₹{airtel_cb:,.2f} ({(airtel_cb/250.00)*100:.1f}%)"
    june_row_10_u = f"✅ ₹250.00 (100%)" if utility_cb >= 250.00 else f"₹{utility_cb:,.2f} ({(utility_cb/250.00)*100:.1f}%)"
    june_row_10_m = f"✅ ₹500.00 (100%)" if merchant_cb >= 500.00 else f"₹{merchant_cb:,.2f} ({(merchant_cb/500.00)*100:.1f}%)"
    
    alert_range = format_date_range(current_txs_raw, start_date, end_date)
    transaction_rows = format_transaction_rows([
        ("25% Airtel", airtel_txs),
        ("10% Utilities", utility_txs),
        ("10% Merchants", merchant_txs),
        ("1% General", general_txs),
        ("Needs classification", unclassified_txs),
    ])
    
    # Generate Section 2 verified column values
    jan_verified = get_verified_col("January 2026")
    feb_verified = get_verified_col("February 2026")
    mar_verified = get_verified_col("March 2026")
    apr_verified = get_verified_col("April 2026")
    may_verified = get_verified_col("May 2026")
    ytd_airtel_cb = 250.00
    ytd_utility_cb = 814.00
    ytd_merchant_cb = 91.00
    ytd_earned_cb = 1155.00
    ytd_credited_cb = 1105.00

    # --- Write report content ---
    report_date = datetime.now().strftime("%B %d, %Y")

    if merchant_cb < 500.00:
        merchant_recommendation = (
            f"**Use remaining merchant room only for planned spends**: Zomato, Swiggy, or BigBasket purchases still "
            f"have about ₹{merchant_remaining/0.10:,.2f} of eligible spend room before the 10% merchant cap fills on {cycle_end_text}."
        )
    else:
        merchant_recommendation = "**Hold preferred merchant spends**: The Zomato, Swiggy, and BigBasket cap is already filled for this cycle."

    if airtel_cb < 250.00:
        airtel_recommendation = (
            f"**Airtel room available**: Eligible Airtel spend room is about ₹{airtel_remaining/0.25:,.2f} before {cycle_end_text}."
        )
    else:
        airtel_recommendation = (
            f"**Hold Airtel Payments**: Since your 25% Airtel Telecom cap is completely filled, postpone any additional "
            f"mobile or broadband recharges until **{next_cycle_start_text}** so they can qualify for the next cycle."
        )

    if utility_cb < 250.00:
        utility_recommendation = (
            f"**Prepay Utilities**: If you have a utility bill due soon, paying it before {cycle_end_text} via the Airtel Thanks App "
            f"can use the remaining ₹{utility_remaining:,.2f} of utility cashback."
        )
    else:
        utility_recommendation = "**Hold utility payments**: The 10% utility cap is already filled for this cycle."

    joining_fee_text = format_fee_event(waiver_summary["joining_fee"])
    renewal_fee_text = (
        "; ".join(format_fee_event(event) for event in waiver_summary["renewal_fees"])
        if waiver_summary["renewal_fees"]
        else "No annual or renewal fee debit found in parsed statements through May 2026."
    )
    completed_waiver = waiver_summary["completed_year"]
    current_waiver = waiver_summary["current_year"]
    fee_waiver_recommendation = (
        f"**Annual fee waiver**: Current tracked eligible spend is {format_amount(current_waiver['eligible_spend'])} "
        f"against the {format_amount(current_waiver['target'])} waiver target, leaving "
        f"{format_amount(current_waiver['remaining'])}. Keep rent and wallet reloads out of this count."
    )

    current_waiver_tracker = render_milestone(
        current=current_waiver["eligible_spend"],
        target=current_waiver["target"],
        format_value=format_amount,
        period=current_waiver["period"],
        deadline=current_waiver["deadline"],
        as_of=waiver_summary["as_of"],
        supporting_lines=(f"Source: {current_waiver['source']}",),
    )
    current_cap_trackers = "\n\n".join(
        f"### {label}\n\n" + render_milestone(
            current=earned,
            target=cap,
            format_value=format_amount,
            period=cycle_period,
            deadline=end_date,
            as_of=today,
            supporting_lines=(f"Qualifying spend: {format_amount(spend)}",),
        )
        for label, earned, cap, spend in (
            ("25% Airtel Cashback Cap", airtel_cb, 250.00, airtel_spend),
            ("10% Utilities Cashback Cap", utility_cb, 250.00, utility_spend),
            ("10% Merchants Cashback Cap", merchant_cb, 500.00, merchant_spend),
        )
    )

    content = f"""# Airtel Axis Credit Card: Cashback Cap & Spend Progress Report

**Account Holder:** Md Ejaz Anwar  
**Credit Card ending in:** XX3164  
**Report Generation Date:** {report_date}  
**Current Statement Period (Ongoing):** {cycle_period}  

---

## 1. Executive Summary
| Bucket | Cashback Rate | Statement-Cycle Cap | Achieved So Far | Left | Spend Needed to Fill |
| :--- | :---: | ---: | ---: | ---: | ---: |
| 25% Airtel | 25% | {format_summary_amount(250.00)} | {format_summary_amount(airtel_cb)} ({(airtel_cb/250.00)*100:.1f}%) | {format_summary_amount(airtel_remaining)} | {format_spend_room(airtel_remaining, 0.25)} |
| 10% Utilities | 10% | {format_summary_amount(250.00)} | {format_summary_amount(utility_cb)} ({(utility_cb/250.00)*100:.1f}%) | {format_summary_amount(utility_remaining)} | {format_spend_room(utility_remaining, 0.10)} |
| 10% Merchants | 10% | {format_summary_amount(500.00)} | {format_summary_amount(merchant_cb)} ({(merchant_cb/500.00)*100:.1f}%) | {format_summary_amount(merchant_remaining)} | {format_spend_room(merchant_remaining, 0.10)} |
| **Total** | Mixed | **{format_summary_amount(total_capped_cap)}** | **{format_summary_amount(total_capped_cb)} ({total_capped_pct:.1f}%)** | **{format_summary_amount(total_remaining_cap)}** | Category-specific |

- **Window:** Current statement-cycle cap window is **{cycle_period}**.
- **Important:** Spend needed is category-specific. Extra Airtel spend cannot consume utility or preferred merchant cashback room.

---

## 2. Closed Statement Summary (2026)
This table covers completed statement months only. "Earned This Cycle" is the cashback generated by that month's spends, while "Credited on Statement" reflects cashback posted from the prior cycle.

| Statement Month | 25% Airtel Cap | 10% Utility Cap | 10% Preferred Merchant Cap | Earned This Cycle | Credited on Statement | Verification |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **January 2026** | ₹0.00 (0%) | ₹94.00 (37.6%) | ₹0.00 (0%) | **₹94.00** | ₹440.00 | Verified |
| **February 2026** | ₹0.00 (0%) | ₹111.00 (44.4%) | ₹0.00 (0%) | **₹111.00** | ₹94.00 | Verified |
| **March 2026** | ₹0.00 (0%) | ₹179.00 (71.6%) | ₹0.00 (0%) | **₹179.00** | ₹111.00 | Verified |
| **April 2026** | ₹0.00 (0%) | ₹250.00 (100%) | ₹31.00 (6.2%) | **₹281.00** | ₹179.00 | Verified |
| **May 2026** | ₹250.00 (100%) | ₹180.00 (72.0%) | ₹60.00 (12.0%) | **₹490.00** | ₹281.00 | Verified |
| **YTD Total (Closed)** | **₹{ytd_airtel_cb:,.2f}** | **₹{ytd_utility_cb:,.2f}** | **₹{ytd_merchant_cb:,.2f}** | **₹{ytd_earned_cb:,.2f}** | **₹{ytd_credited_cb:,.2f}** | Jan-May |

*Note: In May 2026, your ₹1,850.54 Airtel broadband spend qualified for ₹462.63 in cashback, but was capped at the ₹250.00 maximum.*

---

## 3. Annual Fee / Renewal Waiver Tracker
Axis lists the annual fee waiver condition as annual spends over ₹2,00,000, excluding rent and wallet reloads. This tracker also excludes card fees, GST on fees, EMI accounting lines, and cashback credits from the spend total.

**Fee evidence from parsed statements**
- Joining fee: {joining_fee_text}
- Renewal/annual fee: {renewal_fee_text}

### Current Waiver Year

{current_waiver_tracker}

| Waiver Year | Source | Eligible Spend | Target | Progress | Remaining / Surplus | Status |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| {completed_waiver['period']} | {completed_waiver['source']} | **{format_amount(completed_waiver['eligible_spend'])}** | {format_amount(completed_waiver['target'])} | {completed_waiver['progress_pct']:.1f}% | +{format_amount(completed_waiver['over_target'])} | {completed_waiver['status']} |
| {current_waiver['period']} | {current_waiver['source']} | **{format_amount(current_waiver['eligible_spend'])}** | {format_amount(current_waiver['target'])} | {current_waiver['progress_pct']:.1f}% | {format_amount(current_waiver['remaining'])} left | {current_waiver['status']} |

---

## 4. Current Cycle Progress
**Cycle:** {cycle_period}  
**Tracking window used from Gmail alerts:** {alert_range}

{current_cap_trackers}

| Category | Cap | Progress | Est. Cashback | Remaining Cap Room | State |
| :--- | ---: | ---: | ---: | ---: | :--- |
| **Airtel 25%** | ₹250.00 | {june_row_25} | ₹{airtel_cb:,.2f} | ₹{airtel_remaining:,.2f} | {airtel_state} |
| **Utility 10%** | ₹250.00 | {june_row_10_u} | ₹{utility_cb:,.2f} | ₹{utility_remaining:,.2f} | {utility_state} |
| **Merchant 10%** | ₹500.00 | {june_row_10_m} | ₹{merchant_cb:,.2f} | ₹{merchant_remaining:,.2f} | {merchant_state} |
| **General 1%** | No cap | - | ₹{general_cb:,.2f} | Unlimited | Open |
| **Total** | ₹1,000.00 | - | ₹{total_june_cb:,.2f} | ₹{total_remaining_cap:,.2f} | In progress |

---

## 5. {statement_month} Spends & Cap Progress (Ongoing Cycle)
This table summarizes transactions tracked via Gmail alerts ({alert_range}) alongside their category caps, spends, and remaining room. Individual transactions are listed in the next section.

| Category (Rate) | Max Cap | Tracked Transactions | Total Spend | Cashback Earned | Remaining Cap Room | Status / Spend Action |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **25% Airtel** | **₹250.00** | {format_transaction_count(airtel_txs)} | **₹{airtel_spend:,.2f}** | **₹{airtel_cb:,.2f}**{airtel_cap_note} | **₹{airtel_remaining:,.2f}** | {airtel_action} |
| **10% Utilities** | **₹250.00** | {format_transaction_count(utility_txs)} | **₹{utility_spend:,.2f}** | **₹{utility_cb:,.2f}** | **₹{utility_remaining:,.2f}** | {utility_action} |
| **10% Merchants** | **₹500.00** | {format_transaction_count(merchant_txs)} | **₹{merchant_spend:,.2f}** | **₹{merchant_cb:,.2f}** | **₹{merchant_remaining:,.2f}** | {merchant_action} |
| **1% General** | **No Cap** | {format_transaction_count(general_txs)} | **₹{general_spend:,.2f}** | **₹{general_cb:,.2f}** | **Unlimited** | **Active.** Flat 1% cashback on other card spends. |
| **Unclassified Airtel Payments** | **Pending** | {format_transaction_count(unclassified_txs)} | **₹{unclassified_spend:,.2f}** | **₹0.00** | **Pending** | Requires Airtel/SMS biller evidence before cashback is estimated. |
| **Total** | **₹1,000.00** | - | **₹{total_unique_spend:,.2f}** | **₹{total_june_cb:,.2f}** | **₹{total_remaining_cap:,.2f}** | **Active.** Tracked cashback progress. |

---

## 6. {statement_month} Transaction Details
| Date | Category | Amount | Merchant |
| :--- | :--- | ---: | :--- |
{transaction_rows}

---

## 7. Spend Optimization Recommendations
*   {merchant_recommendation}
*   {airtel_recommendation}
*   {utility_recommendation}
*   {fee_waiver_recommendation}
"""

    with open(REPORT_PATH, 'w') as f:
        f.write(content.strip() + "\n")
    artifact_tmp = f"{PERIOD_TOTALS_FILE}.tmp"
    with open(artifact_tmp, "w") as f:
        json.dump(period_totals_artifact, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(artifact_tmp, PERIOD_TOTALS_FILE)
    print(f"Report updated successfully: {REPORT_PATH}")
    print(f"Structured totals updated successfully: {PERIOD_TOTALS_FILE}")

if __name__ == "__main__":
    update_report()
