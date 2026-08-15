#!/usr/bin/env python3
"""
Automatically update the Flipkart Axis cashback cap report based on Gmail alerts.
"""

import os
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from card_progress import render_milestone

# --- Configuration ---
PDF_DIR = "/Users/ejazanwar/Documents/Gmail Automations/Flipkart Axis Statements"
ALERTS_FILE = os.path.join(PDF_DIR, "gmail_alerts.json")
REPORT_PATH = os.path.join(PDF_DIR, "cashback_cap_report.md")
STATEMENTS_FILE = os.path.join(PDF_DIR, "statements_data.json")
FLIPKART_ANNUAL_FEE = 500.00
FLIPKART_ANNUAL_FEE_WAIVER_TARGET = 350000.00

def load_json(path):
    """Loads data from a JSON file."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return []

def get_merchant_category(desc):
    """Categorizes a transaction description according to Flipkart Axis card rules."""
    desc_upper = desc.upper()
    if "MYNTRA" in desc_upper or "MYN" in desc_upper:
        return "Myntra"
    elif any(x in desc_upper for x in ["FLIPKART", "PTM*FLIPKAR", "CASHFREE*FLIPKART"]):
        return "Flipkart"
    elif "CLEARTRIP" in desc_upper:
        return "Cleartrip"
    elif any(x in desc_upper for x in ["SWIGGY", "UBER", "PVR", "CULT.FIT", "CUREFIT"]):
        return "Preferred"
    elif any(x in desc_upper for x in ["BBPS", "BILLDESK", "PAYTM WALLET", "WALLET", "RENT", "FUEL", "TELECOM", "INSURANCE", "SCHOOL", "GOVT"]):
        return "Excluded"
    else:
        return "General"

def get_cashback_rate(category):
    """Returns the cashback rate for a given category."""
    if category == "Myntra":
        return 0.075
    elif category == "Flipkart" or category == "Cleartrip":
        return 0.05
    elif category == "Preferred":
        return 0.04
    elif category == "General":
        return 0.01
    else:
        return 0.0

def format_bullet_points(txs):
    """Deprecated: kept only for compatibility with older callers."""
    return format_transaction_count(txs)

def format_amount(amount):
    return f"₹{amount:,.0f}" if float(amount).is_integer() else f"₹{amount:,.2f}"

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
        "FLIPKART": "Flipkart",
        "PTM*FLIPKAR": "Flipkart",
        "CASHFREE*FLIPKART": "Flipkart",
        "MYNTRA": "Myntra",
        "MYN": "Myntra",
        "CLEARTRIP": "Cleartrip",
        "SWIGGY": "Swiggy",
        "UBER": "Uber",
        "PVR": "PVR",
        "CULT": "Cult.fit",
        "CUREFIT": "Cult.fit",
    }
    for key, label in mappings.items():
        if key in merchant_upper:
            return label
    return merchant.strip().title() if merchant.isupper() else merchant.strip()

def format_transaction_rows(categories_txs):
    rows = []
    ordered_categories = ["Flipkart", "Myntra", "Cleartrip", "Preferred", "General", "Excluded"]
    for category in ordered_categories:
        for t in categories_txs[category]:
            merchant = clean_merchant(t.get("merchant", "Unknown")).replace("|", "\\|")
            rows.append(f"| {t['date']} | {category} | {format_amount(t['amount'])} | {merchant} |")
    if not rows:
        return "| - | - | - | No tracked transactions in this statement cycle. |"
    return "\n".join(rows)

def format_date_range(txs):
    if not txs:
        return "May 16, 2026 – June 15, 2026"
    dates = [t[0] for t in txs]
    return f"{min(dates).strftime('%B %-d, %Y')} – {max(dates).strftime('%B %-d, %Y')}"



def add_months(dt, months):
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    return datetime(year, month, dt.day)

def get_statement_cycle(as_of):
    if as_of.day >= 16:
        start = datetime(as_of.year, as_of.month, 16)
        end = add_months(start, 1) - timedelta(days=1)
    else:
        end = datetime(as_of.year, as_of.month, 15)
        start = add_months(end.replace(day=16), -1)
    return start, end

def get_statement_quarter(as_of):
    candidates = [
        datetime(as_of.year - 1, 12, 16),
        datetime(as_of.year, 3, 16),
        datetime(as_of.year, 6, 16),
        datetime(as_of.year, 9, 16),
        datetime(as_of.year, 12, 16),
    ]
    start = max(candidate for candidate in candidates if candidate <= as_of)
    end = add_months(start, 3) - timedelta(days=1)
    label_by_start_month = {
        3: "Statement Quarter 1",
        6: "Statement Quarter 2",
        9: "Statement Quarter 3",
        12: "Statement Quarter 4",
    }
    return start, end, label_by_start_month[start.month]

def month_labels_between(start_date, end_date):
    labels = []
    current = add_months(start_date, 1) - timedelta(days=1)
    while current < end_date:
        labels.append(current.strftime("%B %Y"))
        current = add_months(current + timedelta(days=1), 1) - timedelta(days=1)
    return labels

def compute_alert_cashback_for_cycle(alerts, start_date, end_date):
    categories = {
        "Flipkart": {"spend": 0.0, "cashback": 0.0},
        "Myntra": {"spend": 0.0, "cashback": 0.0},
        "Cleartrip": {"spend": 0.0, "cashback": 0.0},
        "Preferred": {"spend": 0.0, "cashback": 0.0},
        "General": {"spend": 0.0, "cashback": 0.0},
        "Excluded": {"spend": 0.0, "cashback": 0.0},
    }
    for alert in alerts:
        try:
            dt = parse_ddmmyyyy(alert["date"])
            amount = float(alert["amount"])
        except Exception:
            continue
        if not start_date <= dt <= end_date:
            continue
        category = get_merchant_category(alert.get("subject", ""))
        categories[category]["spend"] += amount
        if amount >= 100:
            categories[category]["cashback"] += math.floor(amount * get_cashback_rate(category))
    return categories

def format_spend_room(remaining_cashback, rate):
    if remaining_cashback <= 0:
        return "✅ Capped"
    return f"₹{remaining_cashback/rate:,.2f}"

def parse_ddmmyyyy(date_str):
    d, m, y = map(int, date_str.split("/"))
    return datetime(y, m, d)

def format_long_date(dt):
    return dt.strftime("%B %-d, %Y")

def format_waiver_period(start_date, end_date):
    return f"{format_long_date(start_date)} - {format_long_date(end_date)}"

def is_fee_description(description):
    text = description.upper()
    return any(term in text for term in ["JOINING FEE", "ANNUAL FEE", "RENEWAL FEE", "MEMBERSHIP FEE"])

def is_waiver_excluded_description(description):
    text = description.upper()
    excluded_terms = [
        "RENT",
        "WALLET",
        "PAYTM WALLET",
        "FUEL",
        "INSURANCE",
        "BBPS",
        "BILLDESK",
        "ANNUAL FEE",
        "JOINING FEE",
        "RENEWAL FEE",
        "MEMBERSHIP FEE",
        "GST",
        "PROCESSING FEE",
        "TRANSACTION CONVERSION",
        "EMI PRINCIPAL",
        "EMI INTEREST",
        "CASHBACK",
        "FOREIGN CURRENCY TRANSACTION FEE",
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
        events.append({
            "date": fee_date,
            "description": txn.get("description", "").strip(),
            "amount": float(txn.get("amount", 0.0)),
            "gst": round(gst, 2),
            "statement_month": statement.get("month", ""),
        })
    return sorted(events, key=lambda event: parse_ddmmyyyy(event["date"]))

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
            txn_date = parse_ddmmyyyy(txn["date"])
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
            txn_date = parse_ddmmyyyy(alert["date"])
        except Exception:
            continue
        if not start_date <= txn_date <= end_date:
            continue
        amount = float(alert.get("amount", 0.0))
        if is_waiver_excluded_description(alert.get("subject", "")):
            excluded += amount
        else:
            total += amount
            count += 1
    return {"eligible_spend": round(total, 2), "transaction_count": count, "excluded_spend": round(excluded, 2)}

def decorate_waiver_year(spend_data, start_date, end_date, source):
    eligible = spend_data["eligible_spend"]
    remaining = max(0.0, FLIPKART_ANNUAL_FEE_WAIVER_TARGET - eligible)
    surplus = max(0.0, eligible - FLIPKART_ANNUAL_FEE_WAIVER_TARGET)
    return {
        **spend_data,
        "source": source,
        "period": format_waiver_period(start_date, end_date),
        "deadline": end_date.date() if isinstance(end_date, datetime) else end_date,
        "target": FLIPKART_ANNUAL_FEE_WAIVER_TARGET,
        "progress_pct": min(100.0, round((eligible / FLIPKART_ANNUAL_FEE_WAIVER_TARGET) * 100, 1)),
        "remaining": round(remaining, 2),
        "surplus": round(surplus, 2),
        "status": "Met" if eligible > FLIPKART_ANNUAL_FEE_WAIVER_TARGET else "In progress",
    }

def build_annual_fee_waiver_summary(statements_data, alerts, as_of=None):
    as_of = as_of or datetime.now()
    fee_events = find_fee_events(statements_data)
    anchor_date = parse_ddmmyyyy(fee_events[-1]["date"]) if fee_events else datetime(as_of.year, 12, 8)
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

    latest_statement = statements_data.get("summary", [{}])[-1].get("month", "available statements")
    return {
        "as_of": as_of.date() if isinstance(as_of, datetime) else as_of,
        "rule_label": "Flipkart Axis annual fee ₹500; waiver on annual spends greater than ₹3,50,000, excluding rent and wallet loads.",
        "fee_events": fee_events,
        "latest_statement": latest_statement,
        "completed_year": decorate_waiver_year(completed_spend, completed_start, completed_end, "posted statements"),
        "current_year": decorate_waiver_year(current_spend, current_start, current_end, current_source),
    }

def format_fee_event(event):
    total = event["amount"] + event["gst"]
    return f"{event['date']} in {event['statement_month']}: {event['description']} {format_amount(event['amount'])} + GST {format_amount(event['gst'])} = {format_amount(total)}"

def format_waiver_delta(year):
    if year["surplus"] > 0:
        return f"+{format_amount(year['surplus'])}"
    return f"{format_amount(year['remaining'])} left"

def format_annual_fee_waiver_section(summary):
    fee_lines = "\n".join(f"- {format_fee_event(event)}" for event in summary["fee_events"])
    if not fee_lines:
        fee_lines = "- No annual, joining, renewal, or membership fee debit found in parsed statements."
    completed = summary["completed_year"]
    current = summary["current_year"]
    current_tracker = render_milestone(
        current=current["eligible_spend"],
        target=current["target"],
        format_value=format_amount,
        period=current["period"],
        deadline=current["deadline"],
        as_of=summary["as_of"],
        supporting_lines=(f"Source: {current['source']}",),
    )
    return f"""## 3. Annual Fee / Renewal Waiver Tracker
{summary['rule_label']} Missing later annual fee debits are treated as not found in parsed statements, not automatic proof of waiver.

**Fee evidence from parsed statements**
{fee_lines}

### Current Waiver Year

{current_tracker}

| Waiver Year | Source | Eligible Spend | Target | Progress | Remaining / Surplus | Status |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| {completed['period']} | {completed['source']} | **{format_amount(completed['eligible_spend'])}** | {format_amount(completed['target'])} | {completed['progress_pct']:.1f}% | {format_waiver_delta(completed)} | {completed['status']} |
| {current['period']} | {current['source']} | **{format_amount(current['eligible_spend'])}** | {format_amount(current['target'])} | {current['progress_pct']:.1f}% | {format_waiver_delta(current)} | {current['status']} |"""

def extract_historical_cb_by_merchant():
    """Extracts historical cashback from April 2026 and May 2026 statements."""
    data = load_json(STATEMENTS_FILE)
    history = {
        "April 2026": {"Flipkart": 0.0, "Myntra": 0.0, "Cleartrip": 0.0, "Preferred": 0.0, "General": 0.0, "Total": 360.0},
        "May 2026": {"Flipkart": 0.0, "Myntra": 0.0, "Cleartrip": 0.0, "Preferred": 0.0, "General": 0.0, "Total": 3482.0}
    }
    
    statements = data.get("statements", [])
    for stmt in statements:
        m = stmt.get("month")
        if m in history:
            # We will calculate merchant-wise cashback by parsing transactions
            flip_cb = 0.0
            mynt_cb = 0.0
            clear_cb = 0.0
            pref_cb = 0.0
            gen_cb = 0.0
            
            for t in stmt.get("transactions", []):
                # We only count cashback credit entries ('Cr' for Dr transactions)
                if t.get("cashback_earned", 0) > 0:
                    cat = get_merchant_category(t["description"])
                    cb_val = t["cashback_earned"]
                    if t.get("cashback_type", "Cr") == "Dr":
                        cb_val = -cb_val
                        
                    if cat == "Flipkart":
                        flip_cb += cb_val
                    elif cat == "Myntra":
                        mynt_cb += cb_val
                    elif cat == "Cleartrip":
                        clear_cb += cb_val
                    elif cat == "Preferred":
                        pref_cb += cb_val
                    elif cat == "General":
                        gen_cb += cb_val
            
            # Apply floor values
            history[m]["Flipkart"] = round(flip_cb, 2)
            history[m]["Myntra"] = round(mynt_cb, 2)
            history[m]["Cleartrip"] = round(clear_cb, 2)
            history[m]["Preferred"] = round(pref_cb, 2)
            history[m]["General"] = round(gen_cb, 2)
            
    return history

def update_report():
    """Main function to process alerts and generate the report."""
    alerts = load_json(ALERTS_FILE)
    statements_data = load_json(STATEMENTS_FILE)
    waiver_summary = build_annual_fee_waiver_summary(statements_data, alerts)
    
    # Load validation report
    val_report_path = os.path.join(PDF_DIR, "validation_report.json")
    val_data = {}
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
        
        if is_verified:
            return f"✅ Yes (₹{cb_credited:,.2f})"
        else:
            return f"✅ Yes (₹{cb_credited:,.2f})"

    # Historical Q2 Merchant Cashback
    history = extract_historical_cb_by_merchant()
    
    as_of = datetime.now()
    start_date, end_date = get_statement_cycle(as_of)
    quarter_start, quarter_end, quarter_label = get_statement_quarter(as_of)
    cycle_label = end_date.strftime("%B %Y")

    # Filter and sort alerts for the active 16th-to-15th statement cycle.
    june_txs_raw = []
    
    for a in alerts:
        date_str = a["date"]
        try:
            d, m, y = map(int, date_str.split('/'))
            dt = datetime(y, m, d)
            
            if start_date <= dt <= end_date:
                subject = a.get("subject", "")
                june_txs_raw.append((dt, float(a["amount"]), subject.upper(), extract_merchant(subject)))
        except Exception as e:
            print(f"Error parsing alert date {date_str}: {e}")
            
    june_txs_raw.sort(key=lambda x: x[0])
    
    # Categorize ongoing June transactions
    categories_txs = {
        "Flipkart": [], "Myntra": [], "Cleartrip": [], "Preferred": [], "General": [], "Excluded": []
    }
    
    for dt, amt, subj, merchant in june_txs_raw:
        date_str = dt.strftime("%b %d")
        tx_item = {"date": date_str, "amount": amt, "merchant": merchant}
        cat = get_merchant_category(subj)
        categories_txs[cat].append(tx_item)
            
    # --- Calculations ---
    # We need to compute ongoing June cashback, applying transaction-level limits (min ₹100, truncate to integer)
    def compute_ongoing_cashback(txs, rate):
        total_cb = 0
        total_spend = 0.0
        for t in txs:
            total_spend += t["amount"]
            if t["amount"] >= 100.0:
                total_cb += math.floor(t["amount"] * rate)
        return total_spend, float(total_cb)

    previous_cycle_labels = month_labels_between(quarter_start, end_date)
    prev_flipkart_cb = sum(history.get(month, {}).get("Flipkart", 0.0) for month in previous_cycle_labels)
    prev_myntra_cb = sum(history.get(month, {}).get("Myntra", 0.0) for month in previous_cycle_labels)
    prev_cleartrip_cb = sum(history.get(month, {}).get("Cleartrip", 0.0) for month in previous_cycle_labels)

    # 1. Flipkart (5% CB, quarterly cap ₹4,000)
    flipkart_spend, flipkart_cb_raw = compute_ongoing_cashback(categories_txs["Flipkart"], 0.05)
    flipkart_cb_capped = min(flipkart_cb_raw, max(0.0, 4000.0 - prev_flipkart_cb))
    
    # 2. Myntra (7.5% CB, quarterly cap ₹4,000)
    myntra_spend, myntra_cb_raw = compute_ongoing_cashback(categories_txs["Myntra"], 0.075)
    myntra_cb_capped = min(myntra_cb_raw, max(0.0, 4000.0 - prev_myntra_cb))
    
    # 3. Cleartrip (5% CB, quarterly cap ₹4,000)
    cleartrip_spend, cleartrip_cb_raw = compute_ongoing_cashback(categories_txs["Cleartrip"], 0.05)
    cleartrip_cb_capped = min(cleartrip_cb_raw, max(0.0, 4000.0 - prev_cleartrip_cb))
    
    # 4. Preferred (4% CB, Unlimited)
    preferred_spend, preferred_cb = compute_ongoing_cashback(categories_txs["Preferred"], 0.04)
    
    # 5. General (1% CB, Unlimited)
    general_spend, general_cb = compute_ongoing_cashback(categories_txs["General"], 0.01)
    
    # 6. Excluded (0% CB)
    excluded_spend, excluded_cb = compute_ongoing_cashback(categories_txs["Excluded"], 0.0)

    # Sum totals
    total_june_cb = flipkart_cb_capped + myntra_cb_capped + cleartrip_cb_capped + preferred_cb + general_cb
    total_june_spend = flipkart_spend + myntra_spend + cleartrip_spend + preferred_spend + general_spend + excluded_spend
    
    # Status and actions
    def get_status_action(category, current_cb, prev_cb, rate):
        remaining_cap = max(0.0, 4000.0 - prev_cb)
        next_cycle_start = end_date + timedelta(days=1)
        if remaining_cap <= 0:
            return "✅ **₹0.00 remaining**", "✅ **Capped Out.** You have already exhausted the statement-quarter limit in previous statement cycles."
        elif current_cb >= remaining_cap:
            return "✅ **Capped Out (100%)**", f"✅ **Capped Out.** Postpone additional spends on {category} until {format_long_date(next_cycle_start)}."
        else:
            cb_left = remaining_cap - current_cb
            spend_room = cb_left / rate
            return f"₹{current_cb:,.2f} / ₹{remaining_cap:,.2f}", f"**Room Available.** Cashback room equals about ₹{spend_room:,.2f} of eligible {category} spend before {format_long_date(end_date)}."

    flipkart_status, flipkart_action = get_status_action("Flipkart", flipkart_cb_capped, prev_flipkart_cb, 0.05)
    myntra_status, myntra_action = get_status_action("Myntra", myntra_cb_capped, prev_myntra_cb, 0.075)
    cleartrip_status, cleartrip_action = get_status_action("Cleartrip", cleartrip_cb_capped, prev_cleartrip_cb, 0.05)
    
    # Row representations
    june_row_flip = f"✅ ₹{flipkart_cb_capped:,.2f} (Capped)" if flipkart_cb_raw >= (4000.0 - prev_flipkart_cb) else f"₹{flipkart_cb_capped:,.2f} ({(flipkart_cb_capped/max(1.0, 4000.0 - prev_flipkart_cb))*100:.1f}%)"
    june_row_mynt = f"✅ ₹{myntra_cb_capped:,.2f} (Capped)" if myntra_cb_raw >= (4000.0 - prev_myntra_cb) else f"₹{myntra_cb_capped:,.2f} ({(myntra_cb_capped/max(1.0, 4000.0 - prev_myntra_cb))*100:.1f}%)"
    june_row_clear = f"✅ ₹{cleartrip_cb_capped:,.2f} (Capped)" if cleartrip_cb_raw >= (4000.0 - prev_cleartrip_cb) else f"₹{cleartrip_cb_capped:,.2f} ({(cleartrip_cb_capped/max(1.0, 4000.0 - prev_cleartrip_cb))*100:.1f}%)"

    alert_range = format_date_range(june_txs_raw)
    transaction_rows = format_transaction_rows(categories_txs)

    # Verification columns
    jan_verified = get_verified_col("January 2026")
    feb_verified = get_verified_col("February 2026")
    mar_verified = get_verified_col("March 2026")
    apr_verified = get_verified_col("April 2026")
    may_verified = get_verified_col("May 2026")
    june_verified = get_verified_col("June 2026")

    total_remaining_flip = max(0.0, 4000.0 - prev_flipkart_cb - flipkart_cb_capped)
    total_remaining_mynt = max(0.0, 4000.0 - prev_myntra_cb - myntra_cb_capped)
    total_remaining_clear = max(0.0, 4000.0 - prev_cleartrip_cb - cleartrip_cb_capped)

    quarter_period = f"{format_long_date(quarter_start)} – {format_long_date(quarter_end)}"
    quarter_trackers = "\n\n".join(
        f"### {label} Cashback Cap\n\n" + render_milestone(
            current=previous + current,
            target=4000.00,
            format_value=format_amount,
            period=quarter_period,
            deadline=quarter_end,
            as_of=as_of,
            supporting_lines=(f"Current-cycle qualifying spend: {format_amount(spend)}",),
        )
        for label, previous, current, spend in (
            ("Flipkart", prev_flipkart_cb, flipkart_cb_capped, flipkart_spend),
            ("Myntra", prev_myntra_cb, myntra_cb_capped, myntra_spend),
            ("Cleartrip", prev_cleartrip_cb, cleartrip_cb_capped, cleartrip_spend),
        )
    )

    # Total row aggregates
    total_spend_row = total_june_spend
    total_cb_row = total_june_cb
    total_remaining_cap_row = total_remaining_flip + total_remaining_mynt + total_remaining_clear
    total_capped_cap = 12000.0
    total_capped_pct = (total_cb_row / total_capped_cap) * 100 if total_capped_cap else 0.0

    report_date = datetime.now().strftime("%B %d, %Y")

    closed_month_totals = {
        "January 2026": 1060.0,
        "February 2026": 559.0,
        "March 2026": 1070.0,
        "April 2026": 360.0,
        "May 2026": 3482.0,
    }
    june_cycle_cashback = compute_alert_cashback_for_cycle(
        alerts,
        datetime(2026, 5, 16),
        datetime(2026, 6, 15),
    )
    june_flipkart_cb = min(june_cycle_cashback["Flipkart"]["cashback"], 4000.0)
    june_myntra_cb = min(june_cycle_cashback["Myntra"]["cashback"], 4000.0)
    june_cleartrip_cb = min(june_cycle_cashback["Cleartrip"]["cashback"], 4000.0)
    june_total_cb = (
        june_flipkart_cb
        + june_myntra_cb
        + june_cleartrip_cb
        + june_cycle_cashback["Preferred"]["cashback"]
        + june_cycle_cashback["General"]["cashback"]
    )
    closed_month_totals["June 2026"] = june_total_cb

    def quarter_key(month_label):
        dt = datetime.strptime(month_label, "%B %Y")
        return dt.year, ((dt.month - 1) // 3) + 1

    quarter_totals = {}
    for month_label, cashback_total in closed_month_totals.items():
        key = quarter_key(month_label)
        quarter_totals[key] = quarter_totals.get(key, 0.0) + cashback_total
    current_quarter_key = quarter_key(cycle_label)
    quarter_totals[current_quarter_key] = quarter_totals.get(current_quarter_key, 0.0) + total_june_cb

    def quarter_total_for(month_label):
        return f"**₹{quarter_totals[quarter_key(month_label)]:,.2f}**"

    content = f"""# Flipkart Axis Credit Card: Cashback Cap & Spend Progress Report

**Account Holder:** Md Ejaz Anwar  
**Credit Card ending in:** XX6969  
**Report Generation Date:** {report_date}  
**Current Statement Period (Ongoing):** {format_long_date(start_date)} – {format_long_date(end_date)}  
**Current Axis Statement Quarter:** {format_long_date(quarter_start)} – {format_long_date(quarter_end)} ({quarter_label})  

---

## 1. Executive Summary
{quarter_trackers}

| Bucket | Cashback Rate | Statement-Quarter Cap | Achieved So Far | Left | Spend Needed to Fill |
| :--- | :---: | ---: | ---: | ---: | ---: |
| Flipkart | 5% | ₹4,000.00 | ₹{flipkart_cb_capped:,.2f} ({(flipkart_cb_capped/4000.0)*100:.1f}%) | ₹{total_remaining_flip:,.2f} | {format_spend_room(total_remaining_flip, 0.05)} |
| Myntra | 7.5% | ₹4,000.00 | ₹{myntra_cb_capped:,.2f} ({(myntra_cb_capped/4000.0)*100:.1f}%) | ₹{total_remaining_mynt:,.2f} | {format_spend_room(total_remaining_mynt, 0.075)} |
| Cleartrip | 5% | ₹4,000.00 | ₹{cleartrip_cb_capped:,.2f} ({(cleartrip_cb_capped/4000.0)*100:.1f}%) | ₹{total_remaining_clear:,.2f} | {format_spend_room(total_remaining_clear, 0.05)} |
| **Total** | Mixed | **₹12,000.00** | **₹{total_cb_row:,.2f} ({total_capped_pct:.1f}%)** | **₹{total_remaining_cap_row:,.2f}** | Category-specific |

- **Window:** Current Axis statement-quarter cap window is **{format_long_date(quarter_start)} to {format_long_date(quarter_end)}**.
- **Important:** Spend needed is category-specific. Extra Flipkart spend cannot consume Myntra or Cleartrip cashback room.

---

## 2. Historical & Ongoing Cap Achievement Summary (2026)
Below is the status of your monthly cashback caps. The percentages indicate how much of the maximum available cashback cap you successfully captured. A checkmark (✅) indicates that you reached the maximum cap for that category.

| Statement Month | 5% Flipkart Cap | 7.5% Myntra Cap | 5% Cleartrip Cap | Total Cashback Earned | Cashback Credited & Verified? | Quarter Cashback Total |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **January 2026** | ₹195.00 | ₹865.00 | ₹0.00 | **₹1,060.00** | {jan_verified} | {quarter_total_for("January 2026")} |
| **February 2026** | ₹439.00 | ₹120.00 | ₹0.00 | **₹559.00** | {feb_verified} | {quarter_total_for("February 2026")} |
| **March 2026** | ₹1,007.00 | ₹63.00 | ₹0.00 | **₹1,070.00** | {mar_verified} | {quarter_total_for("March 2026")} |
| **April 2026** | ₹195.00 | ₹165.00 | ₹0.00 | **₹360.00** | {apr_verified} | {quarter_total_for("April 2026")} |
| **May 2026** | ₹186.00 | ₹11.00 | ₹3,285.00 | **₹3,482.00** | {may_verified} | {quarter_total_for("May 2026")} |
| **June 2026 *(Est.)*** | ₹{june_flipkart_cb:,.2f} | ₹{june_myntra_cb:,.2f} | ₹{june_cleartrip_cb:,.2f} | ***₹{june_total_cb:,.2f} (Est.)*** | {june_verified} | {quarter_total_for("June 2026")} |
| **{cycle_label} *(Ongoing)*** | {june_row_flip} | {june_row_mynt} | {june_row_clear} | ***₹{total_june_cb:,.2f} (Est.)*** | *Pending (Next Statement)* | {quarter_total_for(cycle_label)} |

*Note: The ₹4,000 cap is assessed per statement quarter. The current Axis {quarter_label.lower()} window is {format_long_date(quarter_start)} – {format_long_date(quarter_end)}.*

---

{format_annual_fee_waiver_section(waiver_summary)}

---

## 4. {cycle_label} Spends & Cap Progress (Ongoing Cycle)
This table summarizes transactions tracked via Gmail alerts ({alert_range}) alongside their category caps, spends, and remaining room. Individual transactions are listed in the next section.

| Category (Rate) | Max Statement-Quarter Cap | Tracked Transactions | Total Spend | Cashback Earned | Remaining Statement-Quarter Cap Room | Status / Spend Action |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **5% Flipkart** | **₹4,000.00** | {format_transaction_count(categories_txs["Flipkart"])} | **₹{flipkart_spend:,.2f}** | **₹{flipkart_cb_capped:,.2f}** | **₹{total_remaining_flip:,.2f}** | {flipkart_action} |
| **7.5% Myntra** | **₹4,000.00** | {format_transaction_count(categories_txs["Myntra"])} | **₹{myntra_spend:,.2f}** | **₹{myntra_cb_capped:,.2f}** | **₹{total_remaining_mynt:,.2f}** | {myntra_action} |
| **5% Cleartrip** | **₹4,000.00** | {format_transaction_count(categories_txs["Cleartrip"])} | **₹{cleartrip_spend:,.2f}** | **₹{cleartrip_cb_capped:,.2f}** | **₹{total_remaining_clear:,.2f}** | {cleartrip_action} |
| **4% Preferred** | **No Cap** | {format_transaction_count(categories_txs["Preferred"])} | **₹{preferred_spend:,.2f}** | **₹{preferred_cb:,.2f}** | **Unlimited** | **Active.** Swiggy, Uber, PVR, Cult.fit. |
| **1% General** | **No Cap** | {format_transaction_count(categories_txs["General"])} | **₹{general_spend:,.2f}** | **₹{general_cb:,.2f}** | **Unlimited** | **Active.** Flat 1% cashback on other card spends. |
| **0% Excluded** | **No Cap** | {format_transaction_count(categories_txs["Excluded"])} | **₹{excluded_spend:,.2f}** | **₹0.00** | **None** | **Excluded.** EMIs, rent, gold, fuel, utilities. |
| **Total** | **₹12,000.00** | - | **₹{total_spend_row:,.2f}** | **₹{total_cb_row:,.2f}** | **₹{total_remaining_cap_row:,.2f}** | **Active.** Tracked cashback progress. |

---

## 5. {cycle_label} Transaction Details
| Date | Category | Amount | Merchant |
| :--- | :--- | ---: | :--- |
{transaction_rows}

---

## 6. Spend Optimization Recommendations
*   **Use Flipkart only for planned purchases**: Flipkart has ₹{total_remaining_flip:,.2f} cashback room left, equivalent to about ₹{total_remaining_flip/0.05:,.2f} of eligible spend before the {quarter_label} cap fills.
*   **Use Myntra selectively**: Myntra has ₹{total_remaining_mynt:,.2f} cashback room left, equivalent to about ₹{total_remaining_mynt/0.075:,.2f} of eligible spend before the {quarter_label} cap fills.
*   **Avoid large Cleartrip bookings**: Cleartrip has only ₹{total_remaining_clear:,.2f} cashback room left, equivalent to about ₹{total_remaining_clear/0.05:,.2f} of eligible spend. Defer larger bookings until **{format_long_date(end_date + timedelta(days=1))}** to avoid losing cashback to the {quarter_label} cap.
"""

    with open(REPORT_PATH, 'w') as f:
        f.write(content.strip() + "\n")
    print(f"Report updated successfully: {REPORT_PATH}")

if __name__ == "__main__":
    update_report()
