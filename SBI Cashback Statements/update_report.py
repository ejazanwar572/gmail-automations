#!/usr/bin/env python3
"""
Automatically update the SBI Cashback cap report based on Gmail alerts and statement PDFs.
"""

import os
import re
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from card_progress import render_milestone

PDF_DIR = "/Users/ejazanwar/Documents/Gmail Automations/SBI Cashback Statements"
ALERTS_FILE = os.path.join(PDF_DIR, "gmail_alerts.json")
STATEMENTS_DATA_FILE = os.path.join(PDF_DIR, "statements_data.json")
REPORT_PATH = os.path.join(PDF_DIR, "cashback_cap_report.md")
PASSWORD = "281219950846"
SBI_ANNUAL_FEE = 999.00
SBI_ANNUAL_FEE_WAIVER_TARGET = 200000.00
HISTORICAL_CASHBACK_BY_MONTH = {
    "March 2026": {"online_cb": 531.00, "offline_cb": 0.00},
    "April 2026": {"online_cb": 599.00, "offline_cb": 0.00},
    "May 2026": {"online_cb": 2000.00, "offline_cb": 23.00},
}

def get_env_password(var_name, default=""):
    """Loads a password from environment variable, falling back to a root-level .env file."""
    import os
    val = os.environ.get(var_name)
    if val:
        return val
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for _ in range(3):
        env_path = os.path.join(current_dir, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            if k.strip() == var_name:
                                return v.strip().strip('"').strip("'")
            except Exception:
                pass
        current_dir = os.path.dirname(current_dir)
    return default

PASSWORD = get_env_password("SBI_CASHBACK_PASSWORD", PASSWORD)

def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return []

def clean_desc(desc):
    # Normalize desc to upper case for mapping
    d_upper = desc.strip().upper()
    
    # Prefix match mapping
    mappings = {
        "AMAZONPAYINDIAPRIVATET": "Amazon Pay",
        "AMAZONPAYINDIAPRIVATE": "Amazon Pay",
        "AMAZONIN": "Amazon",
        "ASSPL": "Amazon",
        "FLIPKARTINTERNETPV": "Flipkart",
        "FLIPKARTINTERNETPVTLT": "Flipkart",
        "FLIPKART": "Flipkart",
        "RAZFURLENCO": "Furlenco",
        "ZEPTOMARKETPLACEPRIV": "Zepto",
        "ZEPTOMARKETPLACE": "Zepto",
        "ZEPTO": "Zepto",
        "AKBARONLINEBOOKINGPVT": "Akbar Travels",
        "AKBARONLINE": "Akbar Travels",
        "YATRAONLINELIMITED": "Yatra",
        "YATRAONLINE": "Yatra",
        "OPENAICHATGPTSUBSCR": "OpenAI",
        "OPENAI": "OpenAI",
        "BLINKITECYBS": "Blinkit",
        "BLINKMERCEPVTLTD": "Blinkit",
        "BLINKIT": "Blinkit",
        "RELIANCERETAILLIMITE": "Reliance Retail",
        "RELIANCERETAILLIMITED": "Reliance Retail",
        "INDIGOAIRLINE": "IndiGo",
        "GROQINC": "Groq",
        "AMAZONUTILITIES": "Amazon Utilities",
        "PEPPERFRY": "Pepperfry",
        "TRAVELOGY": "Travelogy",
        "PEPTECHNOLOGIESPR": "Pep Technologies",
        "CLEARTRIPPRIVATELIMI": "Cleartrip",
        "INDIANRAILWAYCATERINGA": "IRCTC",
        "JOBLEADSMEMBERSHI": "JobLeads",
        "RAZDREAMPLUGPAYTECHSOL": "CRED",
        "YOUTUBEGOOGLE": "YouTube",
        "KIERAYAFURNISHINGSPV": "Kieraya Furnishings",
        "BLINKITFOODSLIMIT": "Blinkit",
    }
    
    # Check exact or prefix match
    for k, v in mappings.items():
        if d_upper.startswith(k) or k in d_upper:
            return v
            
    # Default fallback to title case with basic regex cleaning
    desc = re.sub(r'\s+IN\b', '', desc)
    desc = re.sub(r'\s+Bengaluru\b', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s+Bangalore\b', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s+Gurgaon\b', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s+Mumbai\b', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s+Noida\b', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s+Guwahati\b', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s+\(Pay in EMIs\)', '', desc, flags=re.IGNORECASE)
    
    if desc.isupper():
        return desc.title()
    return desc.strip()

def categorize_transaction(desc):
    desc_upper = desc.upper()
    
    # 1. Exclusions
    exclusions = [
        "RENT", "WALLET", "INSURANCE", "UTILITY", "UTILITIES", "POWER", "GAS", 
        "WATER", "ELECTRICITY", "BILLPAY", "TELECOM", "RECHARGE", "SCHOOL", 
        "COLLEGE", "FEES", "UNIVERSITY", "EDUCATION", "STEAM", "EPIC", 
        "TAX", "GOVT", "FUEL", "PETROL", "HPCL", "BPCL", "IOCL", "JEWELLERY",
        "CARD CASHBACK CREDIT", "PAYMENT RECEIVED"
    ]
    if any(x in desc_upper for x in exclusions):
        return "EXCLUDED"
        
    # 2. Known Online
    online = [
        "AMAZON", "ASSPL", "FLIPKART", "ZEPTO", "BLINKIT", "SWIGGY", "ZOMATO", 
        "FURLENCO", "OPENAI", "GROQ", "MEDIUM", "RAZFURLENCO", "RAZ*", 
        "CLEARTAX", "TRAVEL", "TICKET", "BOOKMYSHOW", "PAYTM", "MOBIKWIK", "PHONEPE",
        "YATRA", "AKBAR", "INDIGO", "CLEARTRIP"
    ]
    if any(x in desc_upper for x in online):
        return "ONLINE"
        
    # 3. Known Offline / fallback
    offline = ["RELIANCE RETAIL", "SPAR", "DMART", "CROME", "TRENDS", "LIFESTYLE", "BATA", "STARBUCKS", "MCDONALD"]
    if any(x in desc_upper for x in offline):
        return "OFFLINE"
        
    # Fallback default: since SBI Cashback is primarily used online
    return "ONLINE"

def get_statement_transactions(pdf_path):
    """Parses transaction list from PDF statement."""
    reader = PdfReader(pdf_path)
    reader.decrypt(PASSWORD)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    
    txs = []
    lines = text.split("\n")
    for line in lines:
        match = re.match(r'^(\d{2}\s+[A-Za-z]{3}\s+\d{2})\s+(.*?)\s+([\d,]+\.\d{2})\s+([CD])', line.strip())
        if match:
            date_str = match.group(1).strip()
            desc = match.group(2).strip()
            amount = float(match.group(3).replace(",", "").strip())
            dc = match.group(4).strip()
            
            # Skip payments and cashback credits
            if "PAYMENT RECEIVED" in desc.upper() or "CARD CASHBACK CREDIT" in desc.upper():
                continue
                
            txs.append({
                "date": date_str,
                "description": desc,
                "amount": amount,
                "type": dc # 'D' for debit, 'C' for credit (refunds)
            })
    return txs

def parse_sbi_txn_date(date_str):
    return datetime.strptime(date_str, "%d %b %y")

def parse_alert_date(date_str):
    d, m, y = map(int, date_str.split('/'))
    return datetime(y, m, d)

def format_long_date(dt):
    return dt.strftime("%B %-d, %Y")

def format_waiver_period(start_date, end_date):
    return f"{format_long_date(start_date)} - {format_long_date(end_date)}"

def parse_statement_month(filename):
    match = re.search(r"SBI_Cashback_Statement_(\w+)_(\d{4})\.pdf", filename)
    return f"{match.group(1)} {match.group(2)}" if match else filename

def parse_statement_month_name(month_name):
    return datetime.strptime(month_name, "%B %Y")

def build_sbi_statement_data():
    statements = []
    for filename in sorted(os.listdir(PDF_DIR)):
        if not filename.startswith("SBI_Cashback_Statement_") or not filename.endswith(".pdf"):
            continue
        transactions = get_statement_transactions(os.path.join(PDF_DIR, filename))
        statements.append({
            "month": parse_statement_month(filename),
            "filename": filename,
            "transactions": transactions,
            "transaction_count": len(transactions),
        })
    return {"statements": statements}

def load_sbi_statement_data():
    data = load_json(STATEMENTS_DATA_FILE)
    if isinstance(data, dict) and data.get("statements"):
        return data
    return build_sbi_statement_data()

def is_sbi_fee_description(description):
    text = description.upper()
    return any(term in text for term in ["JOINING FEE", "ANNUAL FEE", "RENEWAL FEE", "MEMBERSHIP FEE"])

def is_sbi_waiver_excluded_description(description):
    text = description.upper()
    if categorize_transaction(description) == "EXCLUDED":
        return True
    excluded_terms = [
        "JOINING FEE",
        "ANNUAL FEE",
        "RENEWAL FEE",
        "MEMBERSHIP FEE",
        "GST",
        "FEE DB",
        "FEES",
        "PROCESSING FEE",
        "EMI",
        "CARD CASHBACK CREDIT",
        "PAYMENT RECEIVED",
    ]
    return any(term in text for term in excluded_terms)

def iter_sbi_statement_transactions(statements_data):
    for statement in statements_data.get("statements", []):
        for txn in statement.get("transactions", []):
            yield statement, txn

def find_sbi_fee_events(statements_data):
    events = []
    for statement, txn in iter_sbi_statement_transactions(statements_data):
        if txn.get("type") != "D" or not is_sbi_fee_description(txn.get("description", "")):
            continue
        events.append({
            "date": txn.get("date"),
            "description": txn.get("description", "").strip(),
            "amount": float(txn.get("amount", 0.0)),
            "statement_month": statement.get("month", ""),
        })
    return sorted(events, key=lambda event: parse_sbi_txn_date(event["date"]))

def get_sbi_waiver_years(anchor_date, as_of):
    current_start = datetime(as_of.year, anchor_date.month, anchor_date.day)
    if as_of < current_start:
        current_start = datetime(as_of.year - 1, anchor_date.month, anchor_date.day)
    current_end = datetime(current_start.year + 1, current_start.month, current_start.day) - timedelta(days=1)
    completed_start = datetime(current_start.year - 1, current_start.month, current_start.day)
    completed_end = current_start - timedelta(days=1)
    return completed_start, completed_end, current_start, current_end

def sbi_statement_eligible_spend(statements_data, start_date, end_date):
    total = 0.0
    count = 0
    excluded = 0.0
    for _, txn in iter_sbi_statement_transactions(statements_data):
        if txn.get("type") != "D":
            continue
        try:
            txn_date = parse_sbi_txn_date(txn["date"])
        except Exception:
            continue
        if not start_date <= txn_date <= end_date:
            continue
        amount = float(txn.get("amount", 0.0))
        if is_sbi_waiver_excluded_description(txn.get("description", "")):
            excluded += amount
        else:
            total += amount
            count += 1
    return {"eligible_spend": round(total, 2), "transaction_count": count, "excluded_spend": round(excluded, 2)}

def sbi_alert_eligible_spend(alerts, start_date, end_date):
    total = 0.0
    count = 0
    excluded = 0.0
    for alert in alerts:
        try:
            txn_date = parse_alert_date(alert["date"])
        except Exception:
            continue
        if not start_date <= txn_date <= end_date:
            continue
        amount = float(alert.get("amount", 0.0))
        subject = alert.get("subject", "")
        if is_sbi_waiver_excluded_description(subject):
            excluded += amount
        else:
            total += amount
            count += 1
    return {"eligible_spend": round(total, 2), "transaction_count": count, "excluded_spend": round(excluded, 2)}

def decorate_sbi_waiver_year(spend_data, start_date, end_date, source):
    eligible = spend_data["eligible_spend"]
    remaining = max(0.0, SBI_ANNUAL_FEE_WAIVER_TARGET - eligible)
    surplus = max(0.0, eligible - SBI_ANNUAL_FEE_WAIVER_TARGET)
    return {
        **spend_data,
        "source": source,
        "period": format_waiver_period(start_date, end_date),
        "deadline": end_date.date() if isinstance(end_date, datetime) else end_date,
        "target": SBI_ANNUAL_FEE_WAIVER_TARGET,
        "progress_pct": min(100.0, round((eligible / SBI_ANNUAL_FEE_WAIVER_TARGET) * 100, 1)),
        "remaining": round(remaining, 2),
        "surplus": round(surplus, 2),
        "status": "Met" if eligible >= SBI_ANNUAL_FEE_WAIVER_TARGET else "In progress",
    }

def build_annual_fee_waiver_summary(statements_data, alerts, as_of=None):
    as_of = as_of or datetime.now()
    fee_events = find_sbi_fee_events(statements_data)
    if fee_events:
        anchor_date = parse_sbi_txn_date(fee_events[-1]["date"])
        blocked_reason = ""
    else:
        anchor_date = datetime(as_of.year, 5, 23)
        blocked_reason = "No annual, renewal, joining, or membership fee debit found in currently parsed SBI statement PDFs."
    completed_start, completed_end, current_start, current_end = get_sbi_waiver_years(anchor_date, as_of)

    completed_spend = sbi_statement_eligible_spend(statements_data, completed_start, completed_end)
    current_statement_spend = sbi_statement_eligible_spend(statements_data, current_start, current_end)
    current_alert_spend = sbi_alert_eligible_spend(alerts, current_start, current_end)
    if current_alert_spend["eligible_spend"] > current_statement_spend["eligible_spend"]:
        current_spend = current_alert_spend
        current_source = "Gmail alerts"
    else:
        current_spend = current_statement_spend
        current_source = "posted statements"

    completed_year = decorate_sbi_waiver_year(completed_spend, completed_start, completed_end, "posted statements")
    if completed_year["eligible_spend"] < SBI_ANNUAL_FEE_WAIVER_TARGET:
        completed_year["status"] = "Not met - fee charged" if fee_events else "Incomplete evidence"

    return {
        "as_of": as_of.date() if isinstance(as_of, datetime) else as_of,
        "rule_label": "CASHBACK SBI Card annual/renewal fee ₹999; waiver on annual spends of ₹2,00,000 or more in the preceding year.",
        "fee_events": fee_events,
        "blocked_reason": blocked_reason,
        "completed_year": completed_year,
        "current_year": decorate_sbi_waiver_year(current_spend, current_start, current_end, current_source),
    }

def format_sbi_fee_event(event):
    return f"{event['date']} in {event['statement_month']}: {event['description']} {format_amount(event['amount'])}"

def format_fee_evidence_rows(events):
    if not events:
        return "| - | - | - | No annual, renewal, joining, or membership fee debit found in currently parsed SBI statement PDFs. |"
    rows = []
    for event in events:
        description = re.sub(r"\s+", " ", event["description"]).strip().replace("|", "\\|")
        rows.append(
            f"| {event['date']} | {event['statement_month']} | {format_amount(event['amount'])} | {description} |"
        )
    return "\n".join(rows)

def format_waiver_delta(year):
    if year["surplus"] > 0:
        return f"+{format_amount(year['surplus'])}"
    return f"{format_amount(year['remaining'])} left"

def format_annual_fee_waiver_section(summary, section_number=6):
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
    return f"""## {section_number}. Annual Fee / Renewal Waiver Tracker
{summary['rule_label']} The tracker excludes non-spend lines such as payments, cashback credits, card fees, GST/fees, EMI accounting lines, and categories already excluded by this workflow.

**Fee evidence from parsed statements**

| Date | Statement | Amount | Evidence |
| :--- | :--- | ---: | :--- |
{format_fee_evidence_rows(summary["fee_events"])}

### Current Waiver Year

{current_tracker}

| Waiver Year | Source | Eligible Spend | Target | Progress | Remaining / Surplus | Status |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| {completed['period']} | {completed['source']} | **{format_amount(completed['eligible_spend'])}** | {format_amount(completed['target'])} | {completed['progress_pct']:.1f}% | {format_waiver_delta(completed)} | {completed['status']} |
| {current['period']} | {current['source']} | **{format_amount(current['eligible_spend'])}** | {format_amount(current['target'])} | {current['progress_pct']:.1f}% | {format_waiver_delta(current)} | {current['status']} |"""

def calculate_statement_cashback(txs):
    online_spend = 0.0
    offline_spend = 0.0
    excluded_spend = 0.0
    
    for t in txs:
        cat = categorize_transaction(t["description"])
        amount = t["amount"]
        if t["type"] == 'C': # Refund
            amount = -amount
            
        if cat == "ONLINE":
            online_spend += amount
        elif cat == "OFFLINE":
            offline_spend += amount
        else:
            excluded_spend += amount
            
    # Calculate cashback
    online_cb = max(0.0, online_spend * 0.05)
    offline_cb = max(0.0, offline_spend * 0.01)
    
    # Apply statement cycle caps (₹2,000 online, ₹2,000 offline)
    online_cb = min(online_cb, 2000.00)
    offline_cb = min(offline_cb, 2000.00)
    
    return online_cb, offline_cb, online_spend, offline_spend

def extract_statement_cashback_earned(pdf_path):
    reader = PdfReader(pdf_path)
    reader.decrypt(PASSWORD)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    pos_cb = text.find("SAVINGS AND BENEFITS SECTION")
    if pos_cb != -1:
        cb_text = text[max(0, pos_cb - 200):pos_cb]
        cb_nums = re.findall(r'\b\d+\b', cb_text)
        clean_nums = []
        for num in cb_nums:
            if f".{num}" not in cb_text and f"{num}." not in cb_text:
                clean_nums.append(num)
        if len(clean_nums) >= 3:
            return float(clean_nums[-3])

    cb_match = re.search(r'Card Cashback\s*\([^\)]*\)#\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)', text)
    if cb_match:
        return float(cb_match.group(1).replace(",", ""))
    return None

def format_amount(amount):
    return f"₹{amount:,.2f}"

def format_transaction_count(txs):
    count = len(txs)
    return f"{count} transaction" if count == 1 else f"{count} transactions"

def format_transaction_rows(groups):
    rows = []
    for category, txs in groups:
        for t in txs:
            merchant = clean_desc(t["description"]).replace("|", "\\|")
            rows.append(f"| {t['date']} | {category} | {format_amount(t['amount'])} | {merchant} |")

    if not rows:
        return "| - | - | - | No tracked transactions in this statement cycle. |"
    return "\n".join(rows)

def get_category_rate_and_cap(category):
    if category == "5% Online":
        return 0.05, 2000.00
    if category == "1% Offline":
        return 0.01, 2000.00
    return 0.0, 0.0

def format_cycle_transaction_rows(groups, online_cap=2000.00):
    rows = []
    cumulative_by_category = {}
    for category, txs in groups:
        rate, cap = get_category_rate_and_cap(category)
        if category == "5% Online":
            cap = online_cap
        cumulative = cumulative_by_category.get(category, 0.0)
        for t in txs:
            merchant = clean_desc(t["description"]).replace("|", "\\|")
            ideal_cashback = round(max(0.0, t["amount"] * rate), 2)
            remaining = max(0.0, cap - cumulative)
            earned = round(min(ideal_cashback, remaining), 2)
            cumulative = round(min(cap, cumulative + earned), 2)
            if rate == 0.0:
                status = "Excluded"
            elif earned == 0.0 and remaining == 0.0:
                status = "Capped"
            elif cumulative >= cap and earned > 0.0:
                status = "Cap Hit"
            else:
                status = "Active"
            rows.append(
                f"| {t['date']} | {category} | {format_amount(t['amount'])} | {merchant} | "
                f"{format_amount(earned)} | {format_amount(cumulative)} | {status} |"
            )
        cumulative_by_category[category] = cumulative

    if not rows:
        return "| - | - | - | No tracked transactions in this statement cycle. | - | - | - |"
    return "\n".join(rows)

def format_tracked_transactions_cell(txs):
    if not txs:
        return "0 transactions"
    return format_transaction_count(txs)

def format_date_range(txs):
    if not txs:
        return "no tracked transactions"
    dates = [t[0] for t in txs]
    return f"{min(dates).strftime('%B %-d, %Y')} – {max(dates).strftime('%B %-d, %Y')}"

def add_months(dt, months):
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    return datetime(year, month, dt.day)

def get_statement_cycle(as_of):
    if as_of.day >= 24:
        start = datetime(as_of.year, as_of.month, 24)
        end = add_months(start, 1) - timedelta(days=1)
    else:
        end = datetime(as_of.year, as_of.month, 23)
        start = add_months(end.replace(day=24), -1)
    return start, end

def format_spend_room(remaining_cashback, rate):
    if remaining_cashback <= 0:
        return "✅ Capped"
    return format_amount(remaining_cashback / rate)

def build_summary(june_online_cb, june_offline_cb, june_total_cb, start_date, end_date, reset_date):
    remaining_online_room = max(0.0, 2000.00 - june_online_cb)
    remaining_offline_room = max(0.0, 2000.00 - june_offline_cb)
    total_cap = 4000.00
    total_remaining_room = remaining_online_room + remaining_offline_room

    online_pct = (june_online_cb / 2000.00) * 100
    offline_pct = (june_offline_cb / 2000.00) * 100
    total_pct = (june_total_cb / total_cap) * 100

    rows = [
        "| Bucket | Cashback Rate | Statement-Cycle Cap | Achieved So Far | Left | Spend Needed to Fill |",
        "| :--- | :---: | ---: | ---: | ---: | ---: |",
        f"| 5% Online | 5% | {format_amount(2000.00)} | {format_amount(june_online_cb)} ({online_pct:.1f}%) | {format_amount(remaining_online_room)} | {format_spend_room(remaining_online_room, 0.05)} |",
        f"| 1% Offline | 1% | {format_amount(2000.00)} | {format_amount(june_offline_cb)} ({offline_pct:.1f}%) | {format_amount(remaining_offline_room)} | {format_spend_room(remaining_offline_room, 0.01)} |",
        f"| **Total** | Mixed | **{format_amount(total_cap)}** | **{format_amount(june_total_cb)} ({total_pct:.1f}%)** | **{format_amount(total_remaining_room)}** | Category-specific |",
    ]

    bullets = [
        f"- **Window:** Current statement-cycle cap window is **{format_long_date(start_date)} to {format_long_date(end_date)}**; 5% online resets on **{format_long_date(reset_date)}**.",
    ]
    if remaining_online_room == 0:
        bullets.append("- **Warning:** 5% online is capped for this cycle. Use a different card for online spends until the reset date if you expect 5% cashback.")
    else:
        bullets.append("- **Important:** Spend needed is category-specific. Online spend cannot consume the 1% offline cashback room.")

    return "\n".join(rows + [""] + bullets)

def build_historical_summary(month_names):
    history = {}
    for month_name in month_names:
        month, year = month_name.split()
        pdf_path = os.path.join(PDF_DIR, f"SBI_Cashback_Statement_{month}_{year}.pdf")
        online_cb = offline_cb = online_spend = offline_spend = 0.0
        statement_cb = None
        if os.path.exists(pdf_path):
            txs = get_statement_transactions(pdf_path)
            online_cb, offline_cb, online_spend, offline_spend = calculate_statement_cashback(txs)
            statement_cb = extract_statement_cashback_earned(pdf_path)
        validated_cashback = HISTORICAL_CASHBACK_BY_MONTH.get(month_name)
        if validated_cashback:
            online_cb = validated_cashback["online_cb"]
            offline_cb = validated_cashback["offline_cb"]
            statement_cb = online_cb + offline_cb
        if statement_cb is None:
            statement_cb = online_cb + offline_cb
        history[month_name] = {
            "online_spend": round(online_spend, 2),
            "online_cb": round(online_cb, 2),
            "offline_spend": round(offline_spend, 2),
            "offline_cb": round(offline_cb, 2),
            "total_spend": round(online_spend + offline_spend, 2),
            "total_cb": round(statement_cb, 2),
        }
    return history

def get_historical_statement_months(statements_data):
    months = {
        statement.get("month")
        for statement in statements_data.get("statements", [])
        if statement.get("month")
    }
    return sorted(months, key=parse_statement_month_name)

def format_historical_rows(history, month_names):
    rows = []
    for month_name in month_names:
        month = history[month_name]
        cap_status = "✅ Capped" if month["online_cb"] >= 2000.00 else "Not capped"
        rows.append(
            f"| **{month_name}** | {format_amount(month['online_spend'])} | "
            f"{format_amount(month['online_cb'])} | "
            f"{format_amount(month['offline_spend'])} | "
            f"{format_amount(month['offline_cb'])} | "
            f"**{format_amount(month['total_spend'])}** | "
            f"**{format_amount(month['total_cb'])}** | {cap_status} |"
        )
    return "\n".join(rows)

def format_cashback_progress(cashback):
    pct = (cashback / 2000.00) * 100
    if cashback >= 2000.00:
        return f"✅ **{format_amount(2000.00)}** *(100.0%)*"
    return f"{format_amount(cashback)} *({pct:.1f}%)*"

def build_total_action(june_online_cb, june_offline_cb, reset_date):
    online_capped = june_online_cb >= 2000.00
    offline_capped = june_offline_cb >= 2000.00
    if online_capped and offline_capped:
        return "✅ **Fully capped.** No cashback cap room remains this cycle."
    if online_capped:
        return f"✅ **Online capped; offline room remains.** Avoid online spends on this card until {format_long_date(reset_date)}."
    if offline_capped:
        return "✅ **Offline capped; online room remains.** Prefer this card only for eligible online spends."
    return "**Active.** Cashback room remains in both eligible categories."

def build_recommendations(june_online_cb, june_offline_cb, reset_date):
    lines = []
    remaining_online_cb = max(0.0, 2000.00 - june_online_cb)
    if remaining_online_cb == 0:
        lines.append(f"*   **Avoid additional online spends on SBI Cashback**: The 5% online cap is already exhausted. Route online purchases through another card until **{format_long_date(reset_date)}**.")
    else:
        lines.append(f"*   **Use remaining 5% online room**: You can still route about {format_amount(remaining_online_cb / 0.05)} of eligible online spend through this card before **{format_long_date(reset_date)}**.")

    remaining_offline_cb = max(0.0, 2000.00 - june_offline_cb)
    if remaining_offline_cb > 0:
        lines.append(f"*   **Offline room remains**: Up to {format_amount(remaining_offline_cb)} offline cashback room remains. Treat this as capacity, not a spending target, because the earn rate is only 1%.")

    lines.append("*   **Avoid excluded categories**: Do not pay utility bills, rent, fuel, education, or wallet loads using this card, as they earn 0% cashback and may incur surcharge fees.")
    return "\n".join(lines)

def update_report():
    # 1. Process ongoing statement-cycle spends using SBI's 24th-to-23rd billing cycle.
    alerts = load_json(ALERTS_FILE)
    statements_data = load_sbi_statement_data()
    waiver_summary = build_annual_fee_waiver_summary(statements_data, alerts)
    june_txs_raw = []
    
    today = datetime.now()
    start_date, end_date = get_statement_cycle(today)
    
    for a in alerts:
        date_str = a["date"]
        try:
            d, m, y = map(int, date_str.split('/'))
            dt = datetime(y, m, d)
            if start_date <= dt <= end_date:
                # Extract merchant from subject (Transaction Alert from CASHBACK SBI Card at <merchant>)
                merchant = "Unknown"
                m_match = re.search(r'at\s+(.*)', a.get("subject", ""), re.IGNORECASE)
                if m_match:
                    merchant = m_match.group(1).strip()
                june_txs_raw.append((dt, float(a["amount"]), merchant))
        except Exception:
            continue
            
    june_txs_raw.sort(key=lambda x: x[0])
    
    # Classify June Spends
    june_online = []
    june_offline = []
    june_excluded = []
    
    for dt, amt, merchant in june_txs_raw:
        date_str = dt.strftime("%b %d")
        tx_item = {"date": date_str, "amount": amt, "description": merchant}
        cat = categorize_transaction(merchant)
        
        if cat == "ONLINE":
            june_online.append(tx_item)
        elif cat == "OFFLINE":
            june_offline.append(tx_item)
        else:
            june_excluded.append(tx_item)
            
    # Calculations for June
    june_online_spend = sum(t["amount"] for t in june_online)
    june_offline_spend = sum(t["amount"] for t in june_offline)
    june_excluded_spend = sum(t["amount"] for t in june_excluded)
    
    june_online_cb = round(min(june_online_spend * 0.05, 2000.00), 2)
    june_offline_cb = round(min(june_offline_spend * 0.01, 2000.00), 2)
    june_total_cb = june_online_cb + june_offline_cb
    june_total_spend = june_online_spend + june_offline_spend + june_excluded_spend
    online_max_cap = 2000.00
    offline_max_cap = 2000.00
    excluded_max_cap = 0.00
    total_max_cap = online_max_cap + offline_max_cap + excluded_max_cap
    total_remaining_cap = max(0.0, online_max_cap - june_online_cb) + max(0.0, offline_max_cap - june_offline_cb)
    alert_range = format_date_range(june_txs_raw)
    reset_date = end_date + timedelta(days=1)
    executive_summary = build_summary(june_online_cb, june_offline_cb, june_total_cb, start_date, end_date, reset_date)
    days_until_reset = max(0, (reset_date.date() - datetime.now().date()).days)
    reset_countdown = f"{days_until_reset} day" if days_until_reset == 1 else f"{days_until_reset} days"
    cashback_trackers = "\n\n".join(
        f"### {label} Cashback Cap\n\n" + render_milestone(
            current=earned,
            target=2000.00,
            format_value=format_amount,
            period=f"{format_long_date(start_date)} – {format_long_date(end_date)}",
            deadline=end_date,
            as_of=today,
            supporting_lines=(f"Qualifying spend: {format_amount(spend)}",),
        )
        for label, earned, spend in (
            ("5% Online", june_online_cb, june_online_spend),
            ("1% Offline", june_offline_cb, june_offline_spend),
        )
    )
    
    # 2. Historical calculations from statement PDFs
    historical_months = get_historical_statement_months(statements_data)
    history = build_historical_summary(historical_months)
    historical_rows = format_historical_rows(history, historical_months)

    # Format recommendations and compact June status cells
    online_action = f"✅ Capped; use another card until {format_long_date(reset_date)}." if june_online_cb >= online_max_cap else f"{format_amount(online_max_cap-june_online_cb)} cashback room left."
    offline_action = "✅ Capped." if june_offline_cb >= offline_max_cap else f"{format_amount(offline_max_cap-june_offline_cb)} cashback room left; use only if needed."
    total_action = build_total_action(june_online_cb, june_offline_cb, reset_date)
    cap_log_rows = format_cycle_transaction_rows([
        ("5% Online", june_online),
        ("1% Offline", june_offline),
        ("0% Excluded", june_excluded),
    ])

    report_date = datetime.now().strftime("%B %d, %Y")
    
    content = f"""# SBI Cashback Credit Card: Cashback Cap & Spend Progress Report

**Account Holder:** Md Ejaz Anwar  
**Credit Card ending in:** XX0846  
**Report Generation Date:** {report_date}  
**Current Statement Period (Ongoing):** {format_long_date(start_date)} – {format_long_date(end_date)}  

---

## 1. Executive Summary
{executive_summary}

---

## 2. Current Cycle Status
**Statement Cycle:** {format_long_date(start_date)} - {format_long_date(end_date)}  
**5% online reset date:** {format_long_date(reset_date)} ({reset_countdown} from report generation)

{cashback_trackers}

| Category | Tracked Transactions | Max Cap | Total Spend | Cashback Earned | Remaining Cap Room | Status |
| :--- | :---: | ---: | ---: | ---: | ---: | :--- |
| **5% Online** | {format_tracked_transactions_cell(june_online)} | **{format_amount(online_max_cap)}** | **{format_amount(june_online_spend)}** | **{format_amount(june_online_cb)}** | **{format_amount(max(0.0, online_max_cap - june_online_cb))}** | {online_action} |
| **1% Offline** | {format_tracked_transactions_cell(june_offline)} | **{format_amount(offline_max_cap)}** | **{format_amount(june_offline_spend)}** | **{format_amount(june_offline_cb)}** | **{format_amount(max(0.0, offline_max_cap - june_offline_cb))}** | {offline_action} |
| **0% Excluded** | {format_tracked_transactions_cell(june_excluded)} | **{format_amount(excluded_max_cap)}** | **{format_amount(june_excluded_spend)}** | **₹0.00** | **₹0.00** | Excluded from cashback. |
| **Total** | {format_transaction_count(june_online + june_offline + june_excluded)} | **{format_amount(total_max_cap)}** | **{format_amount(june_total_spend)}** | **{format_amount(june_total_cb)}** | **{format_amount(total_remaining_cap)}** | {total_action} |

---

## 3. Current Cycle Transaction Cap Log
This table shows estimated cashback by transaction and where the 5% online cap was reached. Transactions after the cap hit show zero incremental 5% cashback.

| Date | Category | Amount | Merchant | Est. Cashback | Cum. Cashback | Cap Status |
| :--- | :--- | ---: | :--- | ---: | ---: | :--- |
{cap_log_rows}

---

## 4. Historical Statement Performance
Closed statement months below show spend, estimated category cashback, official statement cashback, and whether the 5% online cap was reached.

| Statement Month | 5% Online Spend | Est. 5% Online Cashback | 1% Offline Spend | Est. 1% Offline Cashback | Total Eligible Spend | Statement Cashback | Cap Status |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
{historical_rows}

*Note: Category spend and category cashback are workflow estimates from parsed transactions. Statement Cashback is the official cashback earned value extracted from each statement PDF. Eligible spend excludes payment, cashback-credit, fee, and workflow-excluded categories.*

---

{format_annual_fee_waiver_section(waiver_summary, 5)}

---

## 6. Notes / Assumptions
- Current-cycle transactions are based on Gmail alerts from {alert_range}; posted statement totals can differ after settlement, refunds, or delayed posting.
- Historical category cashback is a workflow estimate. The `Statement Cashback` column is the official cashback earned value extracted from the statement PDF.
- Rent, wallet loads, utilities, fuel, education, insurance, tax, payments, cashback credits, and card fees are excluded where this workflow can identify them.
"""

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w') as f:
        f.write(content.strip() + "\n")
    print(f"Report updated successfully: {REPORT_PATH}")

if __name__ == "__main__":
    update_report()
