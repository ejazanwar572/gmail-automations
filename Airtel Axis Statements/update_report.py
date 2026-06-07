#!/usr/bin/env python3
"""
Automatically update the Airtel Axis cashback cap report based on Gmail alerts.
"""

import os
import json
from datetime import datetime

# --- Configuration ---
PDF_DIR = "/Users/ejazanwar/Documents/Gmail Automations/Airtel Axis Statements"
ALERTS_FILE = os.path.join(PDF_DIR, "gmail_alerts.json")
REPORT_PATH = "/Users/ejazanwar/.gemini/antigravity/brain/7e48d011-4f84-4327-bcc1-49d6046b7cdc/cashback_cap_report.md"

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

def format_bullet_points(txs):
    """Formats a list of transactions into a bulleted string."""
    if not txs:
        return "None"
    formatted = []
    for t in txs:
        amt = t['amount']
        amt_str = f"{amt:,.0f}" if amt.is_integer() else f"{amt:,.2f}"
        formatted.append(f"<span style=\"white-space: nowrap;\">{t['date']}: ₹{amt_str}</span>")
    return "<br>".join(formatted)

def update_report():
    """Main function to process alerts and generate the report."""
    alerts = load_json(ALERTS_FILE)
    
    # Filter and sort June 2026 alerts (billing cycle May 13 to June 12)
    june_txs_raw = []
    start_date = datetime(2026, 5, 13)
    end_date = datetime(2026, 6, 12)
    
    for a in alerts:
        date_str = a["date"]
        try:
            # Assuming date format is DD/MM/YYYY
            d, m, y = map(int, date_str.split('/'))
            dt = datetime(y, m, d)
            
            if start_date <= dt <= end_date:
                # Store date object, amount, and subject
                june_txs_raw.append((dt, float(a["amount"]), a.get("subject", "").upper()))
        except ValueError as e:
            print(f"Error parsing date {date_str}: Invalid date format or values. Error: {e}")
        except KeyError as e:
            print(f"Error: Missing required key in alert data: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during date parsing for {date_str}: {e}")
            
    june_txs_raw.sort(key=lambda x: x[0])
    
    # Categorize
    airtel_txs = []
    merchant_txs = []
    general_txs = []
    
    for dt, amt, subj in june_txs_raw:
        date_str = dt.strftime("%b %d")
        tx_item = {"date": date_str, "amount": amt}
        
        if "AIRTEL" in subj:
            airtel_txs.append(tx_item)
        elif any(x in subj for x in ["ZOMATO", "SWIGGY", "BIGBASKET"]):
            merchant_txs.append(tx_item)
        else:
            general_txs.append(tx_item)
            
    # --- Calculations ---
    
    # 25% Airtel
    airtel_spend = sum(t["amount"] for t in airtel_txs)
    airtel_cb = min(airtel_spend * 0.25, 250.00)
    
    if airtel_cb >= 250.00:
        airtel_status = "✅ **₹250.00 *(100%)***"
        airtel_action = "⚠️ **Capped Out.** Postpone any additional Airtel Thanks/telecom recharges until June 13."
    else:
        airtel_status = f"₹{airtel_cb:.2f} *({(airtel_cb/250.00)*100:.1f}%)*"
        airtel_action = f"**Under Cap.** You can pay another ₹{(250.00-airtel_cb)/0.25:.2f} in telecom plans."

    # 10% Utilities (Shared with Airtel App spends)
    utility_spend = airtel_spend
    utility_cb = min(utility_spend * 0.10, 250.00)
    
    if utility_cb >= 250.00:
        utility_status = "✅ **₹250.00 *(100%)***"
        utility_action = "⚠️ **Capped Out.**"
    else:
        utility_status = f"₹{utility_cb:.2f} *({(utility_cb/250.00)*100:.1f}%)*"
        utility_action = f"**Under Cap.** You can pay another ₹{(250.00-utility_cb)/0.10:.2f} in electricity/water/gas bills via Airtel Thanks before June 12."

    # 10% Preferred Merchants
    merchant_spend = sum(t["amount"] for t in merchant_txs)
    merchant_cb = min(merchant_spend * 0.10, 500.00)
    
    if merchant_cb >= 500.00:
        merchant_status = "✅ **₹500.00 *(100%)***"
        merchant_action = "⚠️ **Capped Out.**"
    else:
        merchant_status = f"₹{merchant_cb:.2f} *({(merchant_cb/500.00)*100:.1f}%)*"
        merchant_action = f"**Under Cap.** You have room to spend another ₹{(500.00-merchant_cb)/0.10:.2f} on Zomato, Swiggy, or BigBasket before June 12."

    # 1% General
    general_spend = sum(t["amount"] for t in general_txs)
    general_cb = general_spend * 0.01
    
    total_june_cb = airtel_cb + utility_cb + merchant_cb + general_cb
    
    # Generate Section 2 ongoing row values
    june_row_25 = f"✅ ₹250.00 (100%)" if airtel_cb >= 250.00 else f"₹{airtel_cb:.2f} ({(airtel_cb/250.00)*100:.1f}%)"
    june_row_10_u = f"✅ ₹250.00 (100%)" if utility_cb >= 250.00 else f"₹{utility_cb:.2f} ({(utility_cb/250.00)*100:.1f}%)"
    june_row_10_m = f"✅ ₹500.00 (100%)" if merchant_cb >= 500.00 else f"₹{merchant_cb:.2f} ({(merchant_cb/500.00)*100:.1f}%)"
    
    # Format bullet lists
    airtel_bullets = format_bullet_points(airtel_txs)
    utility_bullets = format_bullet_points(airtel_txs)
    merchant_bullets = format_bullet_points(merchant_txs)
    general_bullets = format_bullet_points(general_txs) if general_txs else "None"
    
    # --- Write report content ---
    report_date = datetime.now().strftime("%B %d, %Y")

    content = f"""# Airtel Axis Credit Card: Cashback Cap & Spend Progress Report

**Account Holder:** Md Ejaz Anwar  
**Credit Card ending in:** XX3164  
**Report Generation Date:** {report_date}  
**Current Statement Period (Ongoing):** May 13, 2026 – June 12, 2026  

---

## 1. Executive Summary
This report combines your historical cashback cashback cap achievement for the calendar year 2026 (Jan–May) with a real-time progress tracker for the ongoing June 2026 cycle. 

Historically, you have used the card strategically, earning rewards almost exclusively in the high-tier **25%** and **10%** categories. Your ongoing cycle has already maxed out the 25% Airtel cap, but you have significant remaining capacity in the preferred merchant (Zomato/Swiggy/BigBasket) and utility cap categories.

---

## 2. Historical & Ongoing Cap Achievement Summary (2026)
Below is the status of your monthly cashback caps. The percentages indicate how much of the maximum available cashback cap you successfully captured. A checkmark (✅) indicates that you reached the maximum cap for that category.

| Statement Month | 25% Airtel Cap (Max: ₹250) | 10% Utility Cap (Max: ₹250) | 10% Preferred Merchant Cap (Max: ₹500) | Total Cashback Earned |
| :--- | :---: | :---: | :---: | :---: |
| **January 2026** | ₹0.00 *(0%)* | ₹94.00 *(37.6%)* | ₹0.00 *(0%)* | **₹94.00** |
| **February 2026** | ₹0.00 *(0%)* | ₹111.00 *(44.4%)* | ₹0.00 *(0%)* | **₹111.00** |
| **March 2026** | ₹0.00 *(0%)* | ₹179.00 *(71.6%)* | ₹0.00 *(0%)* | **₹179.00** |
| **April 2026** | ₹0.00 *(0%)* | ✅ **₹250.00 *(100%)*** | ₹31.00 *(6.2%)* | **₹281.00** |
| **May 2026** | ✅ **₹250.00 *(100%)*** | ₹180.00 *(72.0%)* | ₹60.00 *(12.0%)* | **₹490.00** |
| **June 2026 *(Ongoing)*** | {june_row_25} | *{june_row_10_u}* | *{june_row_10_m}* | ***₹{total_june_cb:.2f} (Est.)*** |

*Note: In May 2026, your ₹1,850.54 Airtel broadband spend qualified for ₹462.63 in cashback, but was capped at the ₹250.00 maximum.*

---

## 3. June 2026 Spends & Cap Progress (Ongoing Cycle)
This combined table aggregates the individual transactions tracked via Gmail alerts (May 13, 2026 – June 7, 2026) alongside their respective category caps, total spends, and remaining room:

| Category (Rate) | Max Cap | Transactions (Date: Amount) | Total Spend | Cashback Earned | Remaining Cap Room | Status / Spend Action |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **25% Airtel** | **₹250.00** | {airtel_bullets} | **₹{airtel_spend:.2f}** | **₹{airtel_cb:.2f}** *(Capped)* | **₹0.00** | {airtel_action} |
| **10% Utilities** | **₹250.00** | {utility_bullets} | **₹{utility_spend:.2f}** | **₹{utility_cb:.2f}** | **₹{250.00 - utility_cb:.2f}** | {utility_action} |
| **10% Merchants** | **₹500.00** | {merchant_bullets} | **₹{merchant_spend:.2f}** | **₹{merchant_cb:.2f}** | **₹{500.00 - merchant_cb:.2f}** | {merchant_action} |
| **1% General** | **No Cap** | {general_bullets} | **₹{general_spend:.2f}** | **₹{general_cb:.2f}** | **Unlimited** | **Active.** Flat 1% cashback on other card spends. |

---

## 4. Spend Optimization Recommendations
*   **Shift Food & Grocery Spends**: If you have any pending grocery or restaurant orders before June 12, routing them through Swiggy, Zomato, or BigBasket will earn you a high 10% return (you have over ₹3,250 of capping room left).
*   **Hold Airtel Payments**: Since your 25% Airtel Telecom cap is completely filled, postpone any additional mobile or broadband recharges until **June 13, 2026** (the start of the July billing cycle) so they can qualify for next month's cap.
*   **Prepay Utilities**: If you have a utility bill (electricity, piped gas, water) due soon, paying it before June 12 via the Airtel Thanks App will lock in the remaining ₹51.28 of utility cashback.
"""

    with open(REPORT_PATH, 'w') as f:
        f.write(content.strip() + "\n")
    print(f"Report updated successfully: {REPORT_PATH}")

if __name__ == "__main__":
    update_report()
