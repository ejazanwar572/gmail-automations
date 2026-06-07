#!/usr/bin/env python3
"""
Three-layer validation of SBI Cashback statement data:
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

PDF_DIR  = "/Users/ejazanwar/Documents/Gmail Automations/SBI Cashback Statements"
PASSWORD = "281219950846"

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
ALERTS_FILE = os.path.join(PDF_DIR, "gmail_alerts.json")

PASS_ICON = "✅"
WARN_ICON = "⚠️ "
FAIL_ICON = "❌"

MONTHS_MAP = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
}

# ─────────────────────────────────────────────────────────────
# Layer 1 Helpers: dual-engine extraction
# ─────────────────────────────────────────────────────────────

def extract_pypdf(pdf_path):
    """Extracts text from PDF using pypdf, decrypting it with password."""
    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        try:
            reader.decrypt(PASSWORD)
        except Exception as e:
            print(f"Error decrypting {pdf_path}: {e}")
            return ""
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def extract_pdftotext(pdf_path):
    """Extracts text from PDF using pdftotext -layout, decrypting it."""
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/pdftotext", "-layout", "-upw", PASSWORD, pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except Exception as e:
        return f"ERROR:{e}"

def grab_amounts(text):
    """Extracts all numeric amounts (including commas) from the text."""
    return set(re.findall(r'[\d,]+\.\d{2}', text))

def extract_key_fields_pdftotext(text):
    """Extracts key fields from pdftotext layout text."""
    fields = {
        "due_date": None,
        "total_due": None,
        "min_due": None,
        "prev_balance": None,
        "payments": None,
        "purchases": None,
        "fees": None,
        "cb_earned": None,
        "cb_credited": None,
    }

    # 1. Dates
    dates = re.findall(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', text)
    if len(dates) >= 2:
        fields["due_date"] = dates[1]

    # 2. Total Due (header)
    total_due_match = re.search(r'\*Total Amount Due[^\n]*\n+\s*([\d,]+\.\d{2})', text)
    if total_due_match:
        fields["total_due"] = total_due_match.group(1).replace(",", "").strip()

    # 3. Min Due (header)
    min_due_match = re.search(r'\*\*Minimum Amount Due\s*\([^\)]*\)\s*\n+(?:[^\n]*\n)?\s*([\d,]+\.\d{2})', text)
    if min_due_match:
        fields["min_due"] = min_due_match.group(1).replace(",", "").strip()

    # 4. Account Summary Row
    summary_pos = text.find("ACCOUNT SUMMARY")
    if summary_pos != -1:
        summary_text = text[summary_pos:summary_pos+1000]
        summary_row = re.search(r'([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})', summary_text)
        if summary_row:
            fields["prev_balance"] = summary_row.group(1).replace(",", "").strip()
            fields["payments"] = summary_row.group(2).replace(",", "").strip()
            fields["purchases"] = summary_row.group(3).replace(",", "").strip()
            fields["fees"] = summary_row.group(4).replace(",", "").strip()
            if "total_due" not in fields or not fields["total_due"]:
                fields["total_due"] = summary_row.group(5).replace(",", "").strip()

    # 5. Cashback Section
    cb_match = re.search(r'Card Cashback\s*\([^\)]*\)#\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)', text)
    if cb_match:
        fields["cb_earned"] = cb_match.group(1).replace(",", "").strip()

    # 6. Credited Cashback
    credit_match = re.search(r'CARD CASHBACK CREDIT\s+([\d,]+\.\d{2})', text)
    if credit_match:
        fields["cb_credited"] = credit_match.group(1).replace(",", "").strip()
    else:
        fields["cb_credited"] = "0.00"

    return fields

def extract_key_fields_pypdf(text):
    """Extracts key fields from pypdf text."""
    fields = {
        "due_date": None,
        "total_due": None,
        "min_due": None,
        "prev_balance": None,
        "payments": None,
        "purchases": None,
        "fees": None,
        "cb_earned": None,
        "cb_credited": None,
    }

    # 1. Dates
    dates = re.findall(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', text)
    if len(dates) >= 2:
        fields["due_date"] = dates[1]
    
    # 2. Supply Floats
    pos_supply = text.find("PLACE OF SUPPLY")
    if pos_supply != -1:
        block_text = text[pos_supply:pos_supply+1000]
        floats = re.findall(r'[\d,]+\.\d{2}', block_text)
        floats = [f.replace(",", "") for f in floats]
        if len(floats) >= 11:
            fields["total_due"] = floats[0]
            fields["min_due"] = floats[1]
            fields["prev_balance"] = floats[10]
            fields["payments"] = floats[6]
            fields["purchases"] = floats[7]
            fields["fees"] = floats[8]

    # 3. Cashback Section in pypdf
    pos_cb = text.find("SAVINGS AND BENEFITS SECTION")
    if pos_cb != -1:
        cb_text = text[max(0, pos_cb-200):pos_cb]
        cb_nums = re.findall(r'\b\d+\b', cb_text)
        clean_nums = []
        for num in cb_nums:
            if f".{num}" not in cb_text and f"{num}." not in cb_text:
                clean_nums.append(num)
        if len(clean_nums) >= 3:
            fields["cb_earned"] = clean_nums[-3]

    # 4. Credited Cashback
    credit_match = re.search(r'CARD CASHBACK CREDIT\s+([\d,]+\.\d{2})', text)
    if credit_match:
        fields["cb_credited"] = credit_match.group(1).replace(",", "").strip()
    else:
        fields["cb_credited"] = "0.00"

    return fields

# ─────────────────────────────────────────────────────────────
# Layer 2 Helper: accounting equation
# ─────────────────────────────────────────────────────────────

def validate_accounting(fields):
    """Validates the accounting equation: Prev Bal - Payments + Purchases + Fees = Total Due"""
    try:
        prev_bal = float(fields["prev_balance"])
        payments = float(fields["payments"])
        purchases = float(fields["purchases"])
        fees = float(fields["fees"])
        total_due = float(fields["total_due"])
    except (ValueError, KeyError, TypeError):
        return None, "Missing or invalid numerical values in fields"

    computed = round(prev_bal - payments + purchases + fees, 2)
    delta = round(abs(computed - total_due), 2)

    return {
        "prev_balance": prev_bal, "payments": payments, "purchases": purchases,
        "fees": fees, "stated_total_due": total_due, "computed_total_due": computed,
        "delta": delta, "match": delta <= 1.0  # allow ₹1 rounding tolerance
    }, None

# ─────────────────────────────────────────────────────────────
# Layer 3 Helper: Gmail alert cross-check
# ─────────────────────────────────────────────────────────────

def get_next_month(month_str):
    try:
        dt = datetime.strptime(month_str, "%B %Y")
        m = dt.month
        y = dt.year
        next_m = m + 1
        next_y = y
        if next_m > 12:
            next_m = 1
            next_y += 1
        return f"{MONTHS_MAP[next_m]} {next_y}"
    except Exception:
        return None

def get_cycle_end_date(month_str):
    try:
        dt = datetime.strptime(month_str, "%B %Y")
        return datetime(dt.year, dt.month, 23)
    except Exception:
        return datetime.now()

def get_mapped_alerts(statement_month_str):
    """Loads and maps Gmail alerts that fall within the statement's billing cycle."""
    if not os.path.exists(ALERTS_FILE):
        return []
    
    with open(ALERTS_FILE, 'r') as f:
        alerts = json.load(f)
    
    # Parse statement month/year e.g. "May 2026"
    try:
        stmt_dt = datetime.strptime(statement_month_str, "%B %Y")
        stmt_m = stmt_dt.month
        stmt_y = stmt_dt.year
    except ValueError:
        return []
    
    # Billing cycle: 24th of (M-1) to 23rd of M
    if stmt_m == 1:
        start_date = datetime(stmt_y - 1, 12, 24)
    else:
        start_date = datetime(stmt_y, stmt_m - 1, 24)
    end_date = datetime(stmt_y, stmt_m, 23)
    
    cycle_alerts = []
    for a in alerts:
        date_str = a["date"]
        try:
            d, m, y = map(int, date_str.split('/'))
            dt = datetime(y, m, d)
            if start_date <= dt <= end_date:
                cycle_alerts.append({"amount": float(a["amount"]), "date": dt})
        except Exception:
            continue
            
    return cycle_alerts

# ─────────────────────────────────────────────────────────────
# Main validation runner
# ─────────────────────────────────────────────────────────────

def run_validation():
    """Executes the full three-layer validation process for all SBI statements."""
    pdf_files = sorted([
        f for f in os.listdir(PDF_DIR)
        if f.endswith('.pdf') and 'SBI_Cashback_Statement' in f
    ])

    month_order = ["March 2026", "April 2026", "May 2026", "June 2026"]

    def sort_key(filename):
        match = re.search(r'Statement_(\w+)_(\d{4})', filename)
        if match:
            month_str = f"{match.group(1)} {match.group(2)}"
            try:
                return month_order.index(month_str)
            except ValueError:
                return 99
        return 99

    pdf_files_sorted = sorted(pdf_files, key=sort_key)

    results = []
    all_pass = True

    print("=" * 90)
    print("  SBI CASHBACK CARD — 3-LAYER DATA VALIDATION REPORT")
    print("=" * 90)

    for pdf_file in pdf_files_sorted:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        
        m_match = re.search(r'Statement_(\w+)_(\d{4})', pdf_file)
        month = f"{m_match.group(1)} {m_match.group(2)}" if m_match else pdf_file

        print(f"\n{'─'*90}")
        print(f"📄 {month}")
        print(f"{'─'*90}")

        text_pypdf    = extract_pypdf(pdf_path)
        text_pdftotext = extract_pdftotext(pdf_path)

        issues = []

        # ── Layer 1: Dual-engine comparison ──────────────────────────
        fields_pypdf     = extract_key_fields_pypdf(text_pypdf)
        fields_pdftotext = extract_key_fields_pdftotext(text_pdftotext)

        print("  LAYER 1 — Dual-engine extraction (pypdf vs pdftotext):")
        for field in ["due_date", "total_due", "min_due", "prev_balance", "payments", "purchases", "fees", "cb_earned", "cb_credited"]:
            v1 = fields_pypdf.get(field)
            v2 = fields_pdftotext.get(field)
            
            if v1 == v2 and v1 is not None:
                print(f"    {PASS_ICON}  {field:<15} = {v1}")
            elif v1 is None or v2 is None:
                print(f"    {WARN_ICON} {field:<15}: one engine returned None  (pypdf={v1}, pdftotext={v2})")
                issues.append(f"L1: {field} — one engine returned None")
            else:
                try:
                    float_v1 = float(v1)
                    float_v2 = float(v2)
                    delta = abs(float_v1 - float_v2)
                    if delta < 0.01:
                        print(f"    {PASS_ICON}  {field:<15}: match (pypdf={v1}, pdftotext={v2})")
                    else:
                        print(f"    {FAIL_ICON} {field:<15}: MISMATCH (pypdf={v1}, pdftotext={v2}) Δ={delta:.2f}")
                        issues.append(f"L1: {field} mismatch Δ={delta:.2f}")
                        all_pass = False
                except ValueError:
                    if v1 != v2:
                        print(f"    {FAIL_ICON} {field:<15}: Non-numeric mismatch (pypdf={v1}, pdftotext={v2})")
                        issues.append(f"L1: {field} non-numeric mismatch")
                        all_pass = False

        # ── Layer 2: Internal accounting equation ──────────────────────────────
        print("  LAYER 2 — Internal accounting equation:")
        acct, err = validate_accounting(fields_pdftotext)
        if acct:
            formula = (f"₹{acct['prev_balance']:,.2f}(prev) "
                       f"- ₹{acct['payments']:,.2f}(pmts) "
                       f"+ ₹{acct['purchases']:,.2f}(buys) "
                       f"+ ₹{acct['fees']:,.2f}(charges)")
            
            if acct["match"]:
                print(f"    {PASS_ICON}  Equation balances: {formula}")
                print(f"           = ₹{acct['computed_total_due']:,.2f} (stated: ₹{acct['stated_total_due']:,.2f}) Δ=₹{acct['delta']:.2f}")
            else:
                print(f"    {FAIL_ICON} Equation FAILS: computed=₹{acct['computed_total_due']:,.2f}, "
                      f"stated=₹{acct['stated_total_due']:,.2f}, Δ=₹{acct['delta']:.2f}")
                issues.append(f"L2: Accounting equation off by ₹{acct['delta']:.2f}")
                all_pass = False
        else:
            print(f"    {WARN_ICON} Could not validate accounting: {err}")
            issues.append(f"L2: Accounting equation validation failed: {err}")

        # ── Layer 3: Gmail alert cross-check ──────────────────────────────────
        print("  LAYER 3 — Gmail transaction alert cross-check:")
        alert_items = get_mapped_alerts(month)
        if alert_items:
            amounts_pypdf     = grab_amounts(text_pypdf)
            amounts_pdftotext = grab_amounts(text_pdftotext)
            pdf_amounts_float = {float(x.replace(',','')) for x in (amounts_pypdf | amounts_pdftotext)}
            
            missing = []
            pending = []
            
            next_month = get_next_month(month)
            next_pdf_amounts = set()
            next_pdf_exists = False
            if next_month:
                next_pdf_name = f"SBI_Cashback_Statement_{next_month.replace(' ', '_')}.pdf"
                next_pdf_path = os.path.join(PDF_DIR, next_pdf_name)
                if os.path.exists(next_pdf_path):
                    next_pdf_exists = True
                    try:
                        next_text_pypdf = extract_pypdf(next_pdf_path)
                        next_text_pdftotext = extract_pdftotext(next_pdf_path)
                        next_pdf_amounts = {float(x.replace(',','')) for x in (grab_amounts(next_text_pypdf) | grab_amounts(next_text_pdftotext))}
                    except Exception:
                        pass
            
            for item in alert_items:
                amt = item["amount"]
                dt = item["date"]
                found_current = any(abs(amt - p_amt) < 0.01 for p_amt in pdf_amounts_float)
                
                if found_current:
                    continue
                    
                # If next PDF exists, check if amount is in next PDF
                if next_pdf_exists:
                    found_next = any(abs(amt - p_amt) < 0.01 for p_amt in next_pdf_amounts)
                    if found_next:
                        continue
                        
                # If next PDF does not exist, and transaction is within 3 days of cycle end, it is pending
                end_date = get_cycle_end_date(month)
                days_to_end = (end_date - dt).days
                if not next_pdf_exists and 0 <= days_to_end <= 3:
                    pending.append(amt)
                else:
                    missing.append(amt)
            
            if not missing and not pending:
                print(f"    {PASS_ICON}  All {len(alert_items)} alert amounts found in PDF (or verified posted in subsequent cycle)")
            else:
                if not missing and pending:
                    print(f"    {WARN_ICON} Alert amounts pending posting in next cycle (near statement cut-off): {pending}")
                if missing:
                    print(f"    {FAIL_ICON} Alert amounts NOT found in PDF: {missing}")
                    issues.append(f"L3: Alert amounts missing from PDF: {missing}")
                    all_pass = False
        else:
            print(f"    {WARN_ICON} No Gmail alert data mapped for this statement cycle")

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
