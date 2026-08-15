#!/usr/bin/env python3
"""
Aggregate spends and cashback monthly across all 3 cards:
Airtel Axis, Flipkart Axis, and SBI Cashback.
"""

import os
import re
import json
import math
import subprocess
from datetime import datetime
from pypdf import PdfReader

# --- Configurations ---
BASE_DIR = "/Users/ejazanwar/Documents/Gmail Automations"
AIRTEL_DIR = os.path.join(BASE_DIR, "Airtel Axis Statements")
FLIPKART_DIR = os.path.join(BASE_DIR, "Flipkart Axis Statements")
SBI_DIR = os.path.join(BASE_DIR, "SBI Cashback Statements")

GLOBAL_REPORT_PATH = os.path.join(BASE_DIR, "aggregate_cashback_report.md")

SBI_PASSWORD = "281219950846"
def get_env_password(var_name, default=""):
    """Loads a password from environment variable, falling back to a root-level .env file."""
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

SBI_PASSWORD = get_env_password("SBI_CASHBACK_PASSWORD", SBI_PASSWORD)

def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return []

def format_money(amount):
    abs_amount = abs(amount)
    sign = "-" if amount < 0 else ""

    if abs_amount >= 100000:
        return f"{sign}₹{abs_amount / 100000:.1f} L"
    if abs_amount >= 1000:
        value = abs_amount / 1000
        formatted = f"{value:.1f}".rstrip("0").rstrip(".")
        return f"{sign}₹{formatted}k"
    if abs_amount == 0:
        return "₹0"
    if abs_amount == round(abs_amount):
        return f"{sign}₹{abs_amount:.0f}"
    return f"{sign}₹{abs_amount:.0f}"

# --- Helper to get next month string ---
def get_next_month_str(month_str):
    try:
        dt = datetime.strptime(month_str, "%B %Y")
        m = dt.month + 1
        y = dt.year
        if m > 12:
            m = 1
            y += 1
        return datetime(y, m, 1).strftime("%B %Y")
    except Exception:
        return None

# --- SBI PDF Parsing ---
def extract_pdftotext(pdf_path):
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/pdftotext", "-layout", "-upw", SBI_PASSWORD, pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except Exception as e:
        return f"ERROR:{e}"

def extract_key_fields_pdftotext(text):
    fields = {
        "purchases": 0.0,
        "cb_earned": 0.0
    }
    # Purchases
    summary_pos = text.find("ACCOUNT SUMMARY")
    if summary_pos != -1:
        summary_text = text[summary_pos:summary_pos+1000]
        summary_row = re.search(r'([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})', summary_text)
        if summary_row:
            fields["purchases"] = float(summary_row.group(3).replace(",", "").strip())
    # Cashback
    cb_match = re.search(r'Card Cashback\s*\([^\)]*\)#\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)', text)
    if cb_match:
        fields["cb_earned"] = float(cb_match.group(1).replace(",", "").strip())
    return fields

# --- Flipkart Axis Helpers ---
def get_merchant_category(desc):
    desc_upper = desc.upper()
    if "MYNTRA" in desc_upper:
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

def extract_historical_fk_cb_by_merchant():
    data = load_json(os.path.join(FLIPKART_DIR, "statements_data.json"))
    history = {
        "April 2026": {"Flipkart": 0.0, "Myntra": 0.0, "Cleartrip": 0.0, "Preferred": 0.0, "General": 0.0, "Total": 360.0},
        "May 2026": {"Flipkart": 0.0, "Myntra": 0.0, "Cleartrip": 0.0, "Preferred": 0.0, "General": 0.0, "Total": 3482.0}
    }
    statements = data.get("statements", []) if isinstance(data, dict) else []
    for stmt in statements:
        m = stmt.get("month")
        if m in history:
            flip_cb, mynt_cb, clear_cb, pref_cb, gen_cb = 0.0, 0.0, 0.0, 0.0, 0.0
            for t in stmt.get("transactions", []):
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
            history[m]["Flipkart"] = round(flip_cb, 2)
            history[m]["Myntra"] = round(mynt_cb, 2)
            history[m]["Cleartrip"] = round(clear_cb, 2)
            history[m]["Preferred"] = round(pref_cb, 2)
            history[m]["General"] = round(gen_cb, 2)
    return history

# --- SBI Cashback Helper ---
def categorize_sbi_transaction(desc):
    desc_upper = desc.upper()
    exclusions = [
        "RENT", "WALLET", "INSURANCE", "UTILITY", "UTILITIES", "POWER", "GAS", 
        "WATER", "ELECTRICITY", "BILLPAY", "TELECOM", "RECHARGE", "SCHOOL", 
        "COLLEGE", "FEES", "UNIVERSITY", "EDUCATION", "STEAM", "EPIC", 
        "TAX", "GOVT", "FUEL", "PETROL", "HPCL", "BPCL", "IOCL", "JEWELLERY",
        "CARD CASHBACK CREDIT", "PAYMENT RECEIVED"
    ]
    if any(x in desc_upper for x in exclusions):
        return "EXCLUDED"
    online = [
        "AMAZON", "ASSPL", "FLIPKART", "ZEPTO", "BLINKIT", "SWIGGY", "ZOMATO", 
        "FURLENCO", "OPENAI", "GROQ", "MEDIUM", "RAZFURLENCO", "RAZ*", 
        "CLEARTAX", "TRAVEL", "TICKET", "BOOKMYSHOW", "PAYTM", "MOBIKWIK", "PHONEPE"
    ]
    if any(x in desc_upper for x in online):
        return "ONLINE"
    offline = ["RELIANCE RETAIL", "SPAR", "DMART", "CROME", "TRENDS", "LIFESTYLE", "BATA", "STARBUCKS", "MCDONALD"]
    if any(x in desc_upper for x in offline):
        return "OFFLINE"
    return "ONLINE"

# --- Main Aggregator ---
def aggregate():
    months = ["January 2026", "February 2026", "March 2026", "April 2026", "May 2026", "June 2026 (Ongoing)"]
    
    data = {m: {
        "Airtel Axis": {"spend": 0.0, "cb": 0.0},
        "Flipkart Axis": {"spend": 0.0, "cb": 0.0},
        "SBI Cashback": {"spend": 0.0, "cb": 0.0},
        "Total": {"spend": 0.0, "cb": 0.0}
    } for m in months}

    # ==========================================
    # 1. Airtel Axis Historical
    # ==========================================
    airtel_data = load_json(os.path.join(AIRTEL_DIR, "statements_data.json"))
    airtel_summary = airtel_data.get("summary", []) if isinstance(airtel_data, dict) else []
    for item in airtel_summary:
        m = item.get("month")
        if m in data:
            spend = float(item.get("debits", 0.0) or 0.0)
            cb = float(item.get("cb_earned", 0.0) or 0.0)
            
            # Fallback if cb is 0 but next month has cb_credited
            if cb == 0.0:
                next_month = get_next_month_str(m)
                for next_item in airtel_summary:
                    if next_item.get("month") == next_month:
                        cb = float(next_item.get("cb_credited", 0.0) or 0.0)
                        break
            
            data[m]["Airtel Axis"]["spend"] = spend
            data[m]["Airtel Axis"]["cb"] = cb

    # ==========================================
    # 2. Flipkart Axis Historical
    # ==========================================
    fk_data = load_json(os.path.join(FLIPKART_DIR, "statements_data.json"))
    fk_summary = fk_data.get("summary", []) if isinstance(fk_data, dict) else []
    for item in fk_summary:
        m = item.get("month")
        if m in data:
            spend = float(item.get("debits", 0.0) or 0.0)
            cb = float(item.get("cb_earned", 0.0) or 0.0)
            
            # Fallback if cb is 0 but next month has cb_credited
            if cb == 0.0:
                next_month = get_next_month_str(m)
                for next_item in fk_summary:
                    if next_item.get("month") == next_month:
                        cb = float(next_item.get("cb_credited", 0.0) or 0.0)
                        break
            
            data[m]["Flipkart Axis"]["spend"] = spend
            data[m]["Flipkart Axis"]["cb"] = cb

    # ==========================================
    # 3. SBI Cashback Historical (Parsed from PDFs)
    # ==========================================
    sbi_files = sorted([
        f for f in os.listdir(SBI_DIR)
        if f.endswith('.pdf') and 'SBI_Cashback_Statement' in f
    ])
    for f in sbi_files:
        m_match = re.search(r'Statement_(\w+)_(\d{4})', f)
        if m_match:
            month_name = f"{m_match.group(1)} {m_match.group(2)}"
            if month_name in data:
                path = os.path.join(SBI_DIR, f)
                txt = extract_pdftotext(path)
                fields = extract_key_fields_pdftotext(txt)
                data[month_name]["SBI Cashback"]["spend"] = fields["purchases"]
                data[month_name]["SBI Cashback"]["cb"] = fields["cb_earned"]

    # ==========================================
    # 4. June 2026 (Ongoing) Calculations
    # ==========================================
    
    # 4a. Airtel Axis June
    airtel_alerts = load_json(os.path.join(AIRTEL_DIR, "gmail_alerts.json"))
    june_start_a = datetime(2026, 5, 13)
    june_end_a = datetime(2026, 6, 12)
    
    june_txs_a = []
    for a in airtel_alerts:
        try:
            d, m, y = map(int, a["date"].split('/'))
            dt = datetime(y, m, d)
            if june_start_a <= dt <= june_end_a:
                june_txs_a.append((float(a["amount"]), a.get("subject", "").upper()))
        except Exception:
            continue
            
    airtel_cat_spends = {"airtel": 0.0, "preferred": 0.0, "general": 0.0}
    for amt, subj in june_txs_a:
        if "AIRTEL" in subj:
            airtel_cat_spends["airtel"] += amt
        elif any(x in subj for x in ["ZOMATO", "SWIGGY", "BIGBASKET"]):
            airtel_cat_spends["preferred"] += amt
        else:
            airtel_cat_spends["general"] += amt
            
    cb_25_a = min(airtel_cat_spends["airtel"] * 0.25, 250.00)
    cb_10_u = min(airtel_cat_spends["airtel"] * 0.10, 250.00)  # Utility spend is treated as airtel_spend in original script
    cb_10_m = min(airtel_cat_spends["preferred"] * 0.10, 500.00)
    cb_1_g = airtel_cat_spends["general"] * 0.01
    
    data["June 2026 (Ongoing)"]["Airtel Axis"]["spend"] = sum(airtel_cat_spends.values())
    data["June 2026 (Ongoing)"]["Airtel Axis"]["cb"] = round(cb_25_a + cb_10_u + cb_10_m + cb_1_g, 2)

    # 4b. Flipkart Axis June
    fk_alerts = load_json(os.path.join(FLIPKART_DIR, "gmail_alerts.json"))
    june_start_fk = datetime(2026, 5, 16)
    june_end_fk = datetime(2026, 6, 15)
    
    june_txs_fk = []
    for a in fk_alerts:
        try:
            d, m, y = map(int, a["date"].split('/'))
            dt = datetime(y, m, d)
            if june_start_fk <= dt <= june_end_fk:
                june_txs_fk.append((float(a["amount"]), a.get("subject", "").upper()))
        except Exception:
            continue
            
    categories_txs_fk = {
        "Flipkart": 0.0, "Myntra": 0.0, "Cleartrip": 0.0, "Preferred": 0.0, "General": 0.0, "Excluded": 0.0
    }
    categories_cb_fk = {
        "Flipkart": 0.0, "Myntra": 0.0, "Cleartrip": 0.0, "Preferred": 0.0, "General": 0.0
    }
    
    fk_history = extract_historical_fk_cb_by_merchant()
    prev_flipkart_cb = fk_history["April 2026"]["Flipkart"] + fk_history["May 2026"]["Flipkart"]
    prev_myntra_cb = fk_history["April 2026"]["Myntra"] + fk_history["May 2026"]["Myntra"]
    prev_cleartrip_cb = fk_history["April 2026"]["Cleartrip"] + fk_history["May 2026"]["Cleartrip"]
    
    for amt, subj in june_txs_fk:
        cat = get_merchant_category(subj)
        categories_txs_fk[cat] += amt
        if amt >= 100.0:
            rate = 0.05 if cat in ["Flipkart", "Cleartrip"] else (0.075 if cat == "Myntra" else (0.04 if cat == "Preferred" else 0.01))
            if cat in categories_cb_fk:
                categories_cb_fk[cat] += math.floor(amt * rate)
                
    flipkart_cb_capped = min(categories_cb_fk["Flipkart"], max(0.0, 4000.0 - prev_flipkart_cb))
    myntra_cb_capped = min(categories_cb_fk["Myntra"], max(0.0, 4000.0 - prev_myntra_cb))
    cleartrip_cb_capped = min(categories_cb_fk["Cleartrip"], max(0.0, 4000.0 - prev_cleartrip_cb))
    
    total_fk_spend = sum(categories_txs_fk.values())
    total_fk_cb = flipkart_cb_capped + myntra_cb_capped + cleartrip_cb_capped + categories_cb_fk["Preferred"] + categories_cb_fk["General"]
    
    data["June 2026 (Ongoing)"]["Flipkart Axis"]["spend"] = total_fk_spend
    data["June 2026 (Ongoing)"]["Flipkart Axis"]["cb"] = round(total_fk_cb, 2)

    # 4c. SBI Cashback June
    sbi_alerts = load_json(os.path.join(SBI_DIR, "gmail_alerts.json"))
    june_start_sbi = datetime(2026, 5, 24)
    june_end_sbi = datetime(2026, 6, 23)
    
    june_txs_sbi = []
    for a in sbi_alerts:
        try:
            d, m, y = map(int, a["date"].split('/'))
            dt = datetime(y, m, d)
            if june_start_sbi <= dt <= june_end_sbi:
                # Extract merchant
                merchant = "Unknown"
                m_match = re.search(r'at\s+(.*)', a.get("subject", ""), re.IGNORECASE)
                if m_match:
                    merchant = m_match.group(1).strip()
                june_txs_sbi.append((float(a["amount"]), merchant))
        except Exception:
            continue
            
    sbi_online_spend = 0.0
    sbi_offline_spend = 0.0
    sbi_excluded_spend = 0.0
    
    for amt, merchant in june_txs_sbi:
        cat = categorize_sbi_transaction(merchant)
        if cat == "ONLINE":
            sbi_online_spend += amt
        elif cat == "OFFLINE":
            sbi_offline_spend += amt
        else:
            sbi_excluded_spend += amt
            
    sbi_online_cb = min(sbi_online_spend * 0.05, 2000.00)
    sbi_offline_cb = min(sbi_offline_spend * 0.01, 2000.00)
    
    data["June 2026 (Ongoing)"]["SBI Cashback"]["spend"] = sbi_online_spend + sbi_offline_spend + sbi_excluded_spend
    data["June 2026 (Ongoing)"]["SBI Cashback"]["cb"] = round(sbi_online_cb + sbi_offline_cb, 2)

    # ==========================================
    # 5. Totals & Output formatting
    # ==========================================
    for m in months:
        t_spend = data[m]["Airtel Axis"]["spend"] + data[m]["Flipkart Axis"]["spend"] + data[m]["SBI Cashback"]["spend"]
        t_cb = data[m]["Airtel Axis"]["cb"] + data[m]["Flipkart Axis"]["cb"] + data[m]["SBI Cashback"]["cb"]
        data[m]["Total"]["spend"] = t_spend
        data[m]["Total"]["cb"] = t_cb

    # Generate Markdown Report
    now_str = datetime.now().strftime("%B %d, %Y")
    
    report = f"""# Monthly Aggregate Spend & Cashback Report

**Account Holder:** Md Ejaz Anwar  
**Report Generation Date:** {now_str}  
**Cards Tracked:**
- **Airtel Axis Bank Credit Card** (XX3164)
- **Flipkart Axis Bank Credit Card** (XX6969)
- **SBI Cashback Credit Card** (XX0846)

---

## 1. 2026 Monthly Aggregate Summary
Below is the aggregated summary of credit card spends, cashback earned, and the effective reward rate across all three cards for the calendar year 2026:

| Month | Airtel Axis Spend | Airtel Axis Cashback | Flipkart Axis Spend | Flipkart Axis Cashback | SBI Cashback Spend | SBI Cashback Earned | Total Spends | Total Cashback Earned | Effective Cashback Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for m in months:
        a_spend = data[m]['Airtel Axis']['spend']
        a_cb = data[m]['Airtel Axis']['cb']
        fk_spend = data[m]['Flipkart Axis']['spend']
        fk_cb = data[m]['Flipkart Axis']['cb']
        sbi_spend = data[m]['SBI Cashback']['spend']
        sbi_cb = data[m]['SBI Cashback']['cb']
        
        tot_spend = data[m]['Total']['spend']
        tot_cb = data[m]['Total']['cb']
        rate = (tot_cb / tot_spend) * 100 if tot_spend > 0 else 0.0
        
        m_bold = f"**{m}**" if "Ongoing" in m else m
        
        report += (
            f"| {m_bold} | {format_money(a_spend)} | {format_money(a_cb)} | "
            f"{format_money(fk_spend)} | {format_money(fk_cb)} | "
            f"{format_money(sbi_spend)} | {format_money(sbi_cb)} | "
            f"**{format_money(tot_spend)}** | **{format_money(tot_cb)}** | **{rate:.2f}%** |\n"
        )

    report += """
*Note: June 2026 values are ongoing and follow each card's current statement cycle cutoffs.*

---

## 2. Card-wise Contribution (YTD 2026)
Below is the cumulative breakdown of spends and cashback earned by each card (transposed):

| Metric | Airtel Axis | Flipkart Axis | SBI Cashback | Total |
| :--- | :---: | :---: | :---: | :---: |
"""

    total_spends_ytd = sum(data[m]['Total']['spend'] for m in months)
    total_cb_ytd = sum(data[m]['Total']['cb'] for m in months)
    
    cards_summary = {
        "Airtel Axis": {"spend": sum(data[m]['Airtel Axis']['spend'] for m in months), "cb": sum(data[m]['Airtel Axis']['cb'] for m in months)},
        "Flipkart Axis": {"spend": sum(data[m]['Flipkart Axis']['spend'] for m in months), "cb": sum(data[m]['Flipkart Axis']['cb'] for m in months)},
        "SBI Cashback": {"spend": sum(data[m]['SBI Cashback']['spend'] for m in months), "cb": sum(data[m]['SBI Cashback']['cb'] for m in months)},
    }
    
    stats = {}
    for card, info in cards_summary.items():
        s_pct = (info["spend"] / total_spends_ytd) * 100 if total_spends_ytd > 0 else 0.0
        c_pct = (info["cb"] / total_cb_ytd) * 100 if total_cb_ytd > 0 else 0.0
        rate = (info["cb"] / info["spend"]) * 100 if info["spend"] > 0 else 0.0
        stats[card] = {
            "spend": format_money(info["spend"]),
            "cb": format_money(info["cb"]),
            "s_pct": f"{s_pct:.1f}%",
            "c_pct": f"{c_pct:.1f}%",
            "rate": f"**{rate:.2f}%**"
        }
        
    ytd_rate = (total_cb_ytd / total_spends_ytd) * 100 if total_spends_ytd > 0 else 0.0
    stats["Total"] = {
        "spend": f"**{format_money(total_spends_ytd)}**",
        "cb": f"**{format_money(total_cb_ytd)}**",
        "s_pct": "**100.0%**",
        "c_pct": "**100.0%**",
        "rate": f"**{ytd_rate:.2f}%**"
    }
    
    report += f"| **Cumulative Spends** | {stats['Airtel Axis']['spend']} | {stats['Flipkart Axis']['spend']} | {stats['SBI Cashback']['spend']} | {stats['Total']['spend']} |\n"
    report += f"| **Cumulative Cashback** | {stats['Airtel Axis']['cb']} | {stats['Flipkart Axis']['cb']} | {stats['SBI Cashback']['cb']} | {stats['Total']['cb']} |\n"
    report += f"| **Share of Total Spends** | {stats['Airtel Axis']['s_pct']} | {stats['Flipkart Axis']['s_pct']} | {stats['SBI Cashback']['s_pct']} | {stats['Total']['s_pct']} |\n"
    report += f"| **Share of Total Cashback** | {stats['Airtel Axis']['c_pct']} | {stats['Flipkart Axis']['c_pct']} | {stats['SBI Cashback']['c_pct']} | {stats['Total']['c_pct']} |\n"
    report += f"| **Effective Rate** | {stats['Airtel Axis']['rate']} | {stats['Flipkart Axis']['rate']} | {stats['SBI Cashback']['rate']} | {stats['Total']['rate']} |\n"

    report += f"""
---

## 3. Key Observations & Optimization Strategies
*   **Highest Yielding Product**: **Flipkart Axis** and **SBI Cashback** drive the highest yields due to the high 5% rewards on Flipkart and other online retailers.
*   **SBI Cashback Cap Impact**: In May 2026, the SBI Cashback card recorded {format_money(data["May 2026"]["SBI Cashback"]["spend"])} of spends and {format_money(data["May 2026"]["SBI Cashback"]["cb"])} cashback, with the effective rate moderated by the {format_money(2000)} online cashback cap and any offline or excluded transaction share.
*   **Spend Distribution**: Grocery, utility, and Airtel spends are best tracked against the **Airtel Axis** category caps. General online spends usually have the strongest cashback room on **SBI Cashback** until the monthly cap is reached, after which **Flipkart Axis** can be the cleaner fallback for uncategorized spends.
"""

    # Write the single canonical report copy.
    with open(GLOBAL_REPORT_PATH, 'w') as f:
        f.write(report.strip() + "\n")
        
    print(f"Aggregate report written to:\n  - {GLOBAL_REPORT_PATH}")

if __name__ == "__main__":
    aggregate()
