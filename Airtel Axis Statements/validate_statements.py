#!/usr/bin/env python3
"""
Three-layer validation of Airtel Axis statement data:
  Layer 1 — Dual-engine extraction: pdftotext vs pypdf (field-level diff)
  Layer 2 — Internal accounting equation: Prev Balance - Payments + Purchases + Charges = Total Due
  Layer 3 — Gmail alert cross-check: compare alert email amounts vs PDF transaction amounts
"""

import os
import re
import json
import subprocess
from pypdf import PdfReader
from datetime import datetime

PDF_DIR  = "/Users/ejazanwar/Documents/Gmail Automations/Airtel Axis Statements"
PASSWORD = "MDEJ2812"

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

PASSWORD = get_env_password("AIRTEL_AXIS_PASSWORD", PASSWORD)
ALERTS_FILE = os.path.join(PDF_DIR, "gmail_alerts.json")

PASS_ICON = "✅"
WARN_ICON = "⚠️ "
FAIL_ICON = "❌"

# Month mapping helper for dates
MONTHS_MAP = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
}

# ─────────────────────────────────────────────────────────────
# Layer 1 Helpers: dual-engine extraction
# ─────────────────────────────────────────────────────────────

def extract_pypdf(pdf_path):
    """Extracts text from PDF using pypdf, handling potential encryption."""
    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        try:
            reader.decrypt(PASSWORD)
        except Exception as e:
            print(f"Error decrypting {pdf_path}: {e}")
            return ""
            
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def extract_pdftotext(pdf_path):
    """Extracts text from PDF using pdftotext, handling potential encryption."""
    try:
        # Use /opt/homebrew/bin/pdftotext as specified in the original context
        result = subprocess.run(
            ["/opt/homebrew/bin/pdftotext", "-opw", PASSWORD, pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except Exception as e:
        return f"ERROR:{e}"

def grab_amounts(text):
    """Extracts all numeric amounts (including commas) from the text."""
    # Finds numbers formatted like X.XX or X,XXX.XX
    return set(re.findall(r'[\d,]+\.\d{2}', text))

def extract_key_fields_pypdf(text):
    """Extracts key fields using regex from pypdf text."""
    cb = re.search(r'Cashback Earned\s+Cashback Credited\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    payment_summary = re.search(
        r'(\d{2}/\d{2}/\d{4})\s*-\s*\d{2}/\d{2}/\d{4}\s+'
        r'(\d{2}/\d{2}/\d{4})\s+\d{2}/\d{2}/\d{4}'
        r'([\d,]+\.\d+)\s*Dr\s+([\d,]+\.\d+)\s*Dr',
        text
    )
    return {
        "due_date":     payment_summary.group(2) if payment_summary else None,
        "total_due":    payment_summary.group(3).replace(',','') if payment_summary else None,
        "min_due":      payment_summary.group(4).replace(',','') if payment_summary else None,
        "cb_earned":    cb.group(1).replace(',','') if cb else None,
        "cb_credited":  cb.group(2).replace(',','') if cb else None,
    }

def extract_key_fields_pdftotext(text):
    """Extracts key fields from vertical pdftotext layout."""
    fields = {
        "due_date": None,
        "total_due": None,
        "min_due": None,
        "cb_earned": None,
        "cb_credited": None
    }
    
    # 1. Payment Summary
    summary_match = re.search(r'PAYMENT SUMMARY(.*?)Credit Card Number', text, re.DOTALL)
    if summary_match:
        lines = [line.strip() for line in summary_match.group(1).split('\n') if line.strip()]
        if len(lines) >= 8:
            # lines[4] is Total Due, lines[5] is Min Due, lines[7] is Due Date
            fields["total_due"] = lines[4].replace('Dr', '').replace('Cr', '').replace(',', '').strip()
            fields["min_due"] = lines[5].replace('Dr', '').replace('Cr', '').replace(',', '').strip()
            fields["due_date"] = lines[7].strip()
            
    # 2. Cashback Details
    cashback_match = re.search(r'CASHBACK DETAILS(.*?)(?:Cashback earned this month|IMPORTANT MESSAGE)', text, re.DOTALL)
    if cashback_match:
        lines = [line.strip() for line in cashback_match.group(1).split('\n') if line.strip()]
        if len(lines) >= 3:
            if lines[1] == "Cashback Earned":
                fields["cb_earned"] = lines[2].replace(',', '').strip()
                if len(lines) >= 4:
                    fields["cb_credited"] = lines[3].replace(',', '').strip()
            else:
                fields["cb_credited"] = lines[1].replace(',', '').strip()
                if len(lines) >= 4:
                    fields["cb_earned"] = lines[3].replace(',', '').strip()
                    
    return fields

# ─────────────────────────────────────────────────────────────
# Layer 2 Helper: accounting equation
# ─────────────────────────────────────────────────────────────

def validate_accounting(text, month):
    """Validates the internal accounting equation."""
    # Pattern designed to capture the flow: Prev Bal - Payments - Credits + Purchases + Cash Advance + Other Charges = Total Due
    # previous balance Dr/Cr tag is optional to support 0.00 previous balances
    pattern = re.search(
        r'([\d,]+\.\d+)(?:\s+(?:Dr|Cr))?\s+'      # 1: Previous Balance (Dr/Cr suffix optional)
        r'([\d,]+\.\d+)\s+'                       # 2: Payments
        r'([\d,]+\.\d+)\s+'                       # 3: Credits
        r'([\d,]+\.\d+)\s+'                       # 4: Purchases
        r'([\d,]+\.\d+)\s+'                       # 5: Cash Advance
        r'([\d,]+\.\d+)\s+'                       # 6: Other Debits/Charges
        r'([\d,]+\.\d+)\s+Dr',                    # 7: Total Payment Due
        text
    )
    if not pattern:
        return None, "Could not find accounting equation line"

    try:
        prev_bal  = float(pattern.group(1).replace(',',''))
        payments  = float(pattern.group(2).replace(',',''))
        credits   = float(pattern.group(3).replace(',',''))
        purchases = float(pattern.group(4).replace(',',''))
        cash_adv  = float(pattern.group(5).replace(',',''))
        other_chg = float(pattern.group(6).replace(',',''))
        total_due = float(pattern.group(7).replace(',',''))
    except ValueError:
        return None, "Error converting extracted numbers to float"

    # Calculation: Prev Balance - Payments - Credits + Purchases + Cash Advance + Other Charges
    computed = round(prev_bal - payments - credits + purchases + cash_adv + other_chg, 2)
    delta    = round(abs(computed - total_due), 2)

    return {
        "prev_balance": prev_bal, "payments": payments, "credits": credits,
        "purchases": purchases, "cash_advance": cash_adv, "other_charges": other_chg,
        "stated_total_due": total_due, "computed_total_due": computed,
        "delta": delta, "match": delta <= 1.0  # allow ₹1 rounding tolerance
    }, None

# ─────────────────────────────────────────────────────────────
# Layer 3 Helper: Gmail alert cross-check (where available)
# ─────────────────────────────────────────────────────────────

def get_mapped_alerts():
    """Loads and maps Gmail alerts by statement month using billing cycle logic."""
    if not os.path.exists(ALERTS_FILE):
        return {}
    with open(ALERTS_FILE, 'r') as f:
        alerts = json.load(f)
    
    mapped = {}
    for a in alerts:
        date_str = a["date"]
        amount = a["amount"]
        try:
            d, m, y = map(int, date_str.split('/'))
            # Statement date is 12th.
            # d <= 12 belongs to month m, d > 12 belongs to month m+1
            if d <= 12:
                statement_m = m
                statement_y = y
            else:
                statement_m = m + 1
                statement_y = y
                if statement_m > 12:
                    statement_m = 1
                    statement_y += 1
            
            month_name = f"{MONTHS_MAP[statement_m]} {statement_y}"
            if month_name not in mapped:
                mapped[month_name] = []
            mapped[month_name].append(amount)
        except Exception as e:
            print(f"Error parsing alert date {date_str}: {e}")
    return mapped

# ─────────────────────────────────────────────────────────────
# Main validation runner
# ─────────────────────────────────────────────────────────────

def run_validation():
    """Executes the full three-layer validation process for all PDF statements."""
    pdf_files = sorted([
        f for f in os.listdir(PDF_DIR)
        if f.endswith('.pdf') and 'Airtel_Axis_Statement' in f
    ])

    # Define the expected chronological order of months
    month_order = ["April 2025","May 2025","June 2025","July 2025","August 2025",
                   "September 2025","October 2025","November 2025","December 2025",
                   "January 2026","February 2026","March 2026","April 2026","May 2026"]

    # Sort files based on the expected month order
    def sort_key(filename):
        match = re.search(r'Statement_(\w+)_(\d{4})', filename)
        if match:
            month_str = f"{match.group(1)} {match.group(2)}"
            try:
                return month_order.index(month_str)
            except ValueError:
                return 99 # Fallback for unmatched names
        return 99

    pdf_files_sorted = sorted(pdf_files, key=sort_key)

    # Load and map alerts
    alerts_by_month = get_mapped_alerts()

    results = []
    all_pass = True

    print("=" * 90)
    print("  AIRTEL AXIS CARD — 3-LAYER DATA VALIDATION REPORT")
    print("=" * 90)

    for pdf_file in pdf_files_sorted:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        
        m_match = re.search(r'Statement_(\w+)_(\d{4})', pdf_file)
        month = f"{m_match.group(1)} {m_match.group(2)}" if m_match else pdf_file

        print(f"\n{'─'*90}")
        print(f"📄 {month}")
        print(f"{'─'*90}")

        # --- Extraction ---
        text_pypdf    = extract_pypdf(pdf_path)
        text_pdftotext = extract_pdftotext(pdf_path)

        issues = []

        # ── Layer 1: Dual-engine key-field comparison ──────────────────────────
        fields_pypdf     = extract_key_fields_pypdf(text_pypdf)
        fields_pdftotext = extract_key_fields_pdftotext(text_pdftotext)

        print("  LAYER 1 — Dual-engine extraction (pypdf vs pdftotext):")
        for field in ["due_date", "total_due", "min_due", "cb_earned", "cb_credited"]:
            v1 = fields_pypdf.get(field)
            v2 = fields_pdftotext.get(field)
            
            if v1 == v2 and v1 is not None:
                print(f"    {PASS_ICON}  {field:<15} = {v1}")
            elif v1 is None or v2 is None:
                print(f"    {WARN_ICON} {field:<15}: one engine returned None  (pypdf={v1}, pdftotext={v2})")
                issues.append(f"L1: {field} — one engine returned None")
            else:
                try:
                    # Attempt numeric comparison
                    float_v1 = float(v1.replace(',', '')) if v1 else None
                    float_v2 = float(v2.replace(',', '')) if v2 else None
                    
                    if float_v1 is None or float_v2 is None:
                        print(f"    {FAIL_ICON} {field:<15}: Type mismatch (pypdf={v1}, pdftotext={v2})")
                        issues.append(f"L1: {field} type mismatch")
                        all_pass = False
                        continue

                    delta = abs(float_v1 - float_v2)
                    if delta < 1.0:
                        print(f"    {PASS_ICON}  {field:<15}: match (pypdf={v1}, pdftotext={v2}) Δ={delta:.2f}")
                    else:
                        print(f"    {FAIL_ICON} {field:<15}: MISMATCH (pypdf={v1}, pdftotext={v2}) Δ={delta:.2f}")
                        issues.append(f"L1: {field} mismatch Δ={delta:.2f}")
                        all_pass = False
                except ValueError:
                    if v1 != v2:
                        print(f"    {FAIL_ICON} {field:<15}: Non-numeric mismatch (pypdf={v1}, pdftotext={v2})")
                        issues.append(f"L1: {field} non-numeric mismatch")
                        all_pass = False

        # Amount set comparison
        amounts_pypdf     = grab_amounts(text_pypdf)
        amounts_pdftotext = grab_amounts(text_pdftotext)
        only_in_pypdf     = amounts_pypdf - amounts_pdftotext
        only_in_pdftotext = amounts_pdftotext - amounts_pypdf
        if only_in_pypdf or only_in_pdftotext:
            print(f"    {WARN_ICON} Amount-set diff: {len(only_in_pypdf)} amounts only in pypdf, "
                  f"{len(only_in_pdftotext)} only in pdftotext")
        else:
            print(f"    {PASS_ICON}  All numeric amounts match between both engines")

        # ── Layer 2: Internal accounting equation ──────────────────────────────
        print("  LAYER 2 — Internal accounting equation:")
        acct, err = validate_accounting(text_pypdf, month)
        if err:
            acct, err2 = validate_accounting(text_pdftotext, month)
        
        if acct:
            formula = (f"₹{acct['prev_balance']:,.2f}(prev) "
                       f"- ₹{acct['payments']:,.2f}(pmts) "
                       f"- ₹{acct['credits']:,.2f}(creds) "
                       f"+ ₹{acct['purchases']:,.2f}(buys) "
                       f"+ ₹{acct['cash_advance']:,.2f}(cash) "
                       f"+ ₹{acct['other_charges']:,.2f}(chgs)")
            
            if acct["match"]:
                print(f"    {PASS_ICON}  Equation balances: {formula}")
                print(f"           = ₹{acct['computed_total_due']:,.2f} (stated: ₹{acct['stated_total_due']:,.2f}) Δ=₹{acct['delta']:.2f}")
            else:
                print(f"    {FAIL_ICON} Equation FAILS: computed=₹{acct['computed_total_due']:,.2f}, "
                      f"stated=₹{acct['stated_total_due']:,.2f}, Δ=₹{acct['delta']:.2f}")
                issues.append(f"L2: Accounting equation off by ₹{acct['delta']:.2f}")
                all_pass = False
        else:
            print(f"    {WARN_ICON} Could not locate accounting equation line")
            issues.append("L2: Accounting equation line not found")

        # ── Layer 3: Gmail alert cross-check ──────────────────────────────────
        print("  LAYER 3 — Gmail transaction alert cross-check:")
        if month in alerts_by_month:
            alert_amounts = alerts_by_month[month]
            
            pdf_amounts_float = {float(x.replace(',','')) for x in (amounts_pypdf | amounts_pdftotext)}
            
            missing = []
            for amt in alert_amounts:
                if not any(abs(amt - p_amt) < 0.01 for p_amt in pdf_amounts_float):
                    missing.append(amt)
            
            if not missing:
                print(f"    {PASS_ICON}  All {len(alert_amounts)} alert amounts found in PDF: {sorted(alert_amounts)}")
            else:
                print(f"    {FAIL_ICON} Alert amounts NOT found in PDF: {missing}")
                issues.append(f"L3: Alert amounts missing from PDF: {missing}")
                all_pass = False
        else:
            print(f"    {WARN_ICON} No Gmail alert data for this month")

        # ── Summary ───────────────────────────────────────────────────────────
        if not issues:
            print(f"\n  🟢 VERDICT: FULLY VALIDATED — no discrepancies found")
        else:
            print(f"\n  🔴 VERDICT: {len(issues)} issue(s) found:")
            for iss in issues:
                print(f"     • {iss}")

        results.append({"month": month, "issues": issues, "validated": len(issues) == 0})

    # ── Global summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*90}")
    print("  GLOBAL VALIDATION SUMMARY")
    print(f"{'='*90}")
    validated = [r for r in results if r["validated"]]
    flagged   = [r for r in results if not r["validated"]]
    print(f"  {PASS_ICON}  Fully validated: {len(validated)}/{len(results)} statements")
    if flagged:
        print(f"  {FAIL_ICON} Statements with issues ({len(flagged)}):")
        for r in flagged:
            print(f"     • {r['month']}: {'; '.join(r['issues'])}")
    else:
        print(f"  🟢 ALL {len(results)} STATEMENTS PASSED VALIDATION")

    report_path = os.path.join(PDF_DIR, "validation_report.json")
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  Report saved → {report_path}")

if __name__ == "__main__":
    run_validation()
