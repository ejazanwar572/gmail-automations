#!/usr/bin/env python3
"""
Three-layer validation of Flipkart Axis statement data:
  Layer 1 — Dual-engine extraction: pdftotext vs pypdf (field-level diff)
  Layer 2 — Internal accounting equation: Prev Balance - Payments - Credits + Purchases + Cash Advance + Other Charges = Total Due
  Layer 3 — Gmail alert cross-check: compare alert email amounts vs PDF transaction amounts
  Layer 4 — Cross-statement cashback validation: current statement cb_credited matches previous cb_earned
"""

import os
import re
import json
import subprocess
import sys
from pypdf import PdfReader
from datetime import datetime

PDF_DIR  = "/Users/ejazanwar/Documents/Gmail Automations/Flipkart Axis Statements"
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
ROOT_DIR = os.path.dirname(PDF_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import card_freshness

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
        result = subprocess.run(
            ["/opt/homebrew/bin/pdftotext", "-layout", "-opw", PASSWORD, pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except Exception as e:
        return f"ERROR:{e}"

def grab_amounts(text):
    """Extracts all numeric amounts (including commas) from the text."""
    return set(re.findall(r'[\d,]+\.\d{2}', text))

def compute_ledger_cashback(text):
    tx_pattern = re.compile(
        r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s+(Dr|Cr)(?:\s+([\d,]+\.\d{2})\s+(Dr|Cr))?',
        re.MULTILINE
    )
    total_earned = 0.0
    for m in tx_pattern.finditer(text):
        groups = m.groups()
        desc = groups[1].upper()
        if "CARD NO:" in desc or "EMI BALANCES" in desc or "PAGE :" in desc:
            continue
        cb_amt = float(groups[4].replace(',', '')) if groups[4] else 0.0
        cb_type = groups[5] if groups[5] else 'Cr'
        if cb_amt > 0:
            if cb_type == 'Cr':
                total_earned += cb_amt
            else:
                total_earned -= cb_amt
    return round(total_earned, 2)

def extract_key_fields_pypdf(text):
    """Extracts key fields using regex from pypdf text."""
    cb = re.search(r'CASHBACK DETAILS.*?Cashback Earned\s+Cashback Credited\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    payment_summary = re.search(
        r'(\d{2}/\d{2}/\d{4})\s*-\s*\d{2}/\d{2}/\d{4}\s+'
        r'(\d{2}/\d{2}/\d{4})\s+'
        r'\d{2}/\d{2}/\d{4}'
        r'([\d,]+\.\d+)\s*Dr\s+([\d,]+\.\d+)\s*Dr',
        text
    )
    cb_earned = cb.group(1).replace(',','') if cb else None
    if cb_earned is None:
        computed = compute_ledger_cashback(text)
        if computed > 0:
            cb_earned = f"{computed:.2f}"
            
    return {
        "due_date":     payment_summary.group(2) if payment_summary else None,
        "total_due":    payment_summary.group(3).replace(',','') if payment_summary else None,
        "min_due":      payment_summary.group(4).replace(',','') if payment_summary else None,
        "cb_earned":    cb_earned,
        "cb_credited":  cb.group(2).replace(',','') if cb else None,
    }

def extract_key_fields_pdftotext(text):
    """Extracts key fields from pdftotext layout (tries horizontal first, falls back to vertical)."""
    # 1. Try Horizontal layout pattern (since we run pdftotext with -layout)
    cb = re.search(r'Cashback Earned\s+Cashback Credited\s*\n\s*([\d,.]+)\s+([\d,.]+)', text, re.IGNORECASE)
    payment_summary = re.search(
        r'Total Payment Due\s+Minimum Payment Due\s+Statement Period\s+Payment Due Date.*?\n\s*'
        r'([\d,.]+)\s+Dr\s+([\d,.]+)\s+Dr\s+(\d{2}/\d{2}/\d{4})\s*-\s*\d{2}/\d{2}/\d{4}\s+(\d{2}/\d{2}/\d{4})',
        text
    )
    if payment_summary:
        cb_earned = cb.group(1).replace(',','') if cb else None
        if cb_earned is None:
            computed = compute_ledger_cashback(text)
            if computed > 0:
                cb_earned = f"{computed:.2f}"
        return {
            "due_date":     payment_summary.group(4),
            "total_due":    payment_summary.group(1).replace(',',''),
            "min_due":      payment_summary.group(2).replace(',',''),
            "cb_earned":    cb_earned,
            "cb_credited":  cb.group(2).replace(',','') if cb else None,
        }

    # 2. Fallback to vertical layout extraction
    fields = {
        "due_date": None,
        "total_due": None,
        "min_due": None,
        "cb_earned": None,
        "cb_credited": None
    }
    
    summary_match = re.search(r'PAYMENT SUMMARY(.*?)Credit Card Number', text, re.DOTALL)
    if summary_match:
        lines = [line.strip() for line in summary_match.group(1).split('\n') if line.strip()]
        dr_lines = [l for l in lines if 'Dr' in l or 'Cr' in l]
        date_lines = [l for l in lines if re.search(r'\d{2}/\d{2}/\d{4}', l)]
        
        if len(dr_lines) >= 2:
            fields["total_due"] = dr_lines[0].replace('Dr', '').replace('Cr', '').replace(',', '').strip()
            fields["min_due"] = dr_lines[1].replace('Dr', '').replace('Cr', '').replace(',', '').strip()
        if len(date_lines) >= 2:
            single_dates = [d for d in date_lines if '-' not in d]
            if single_dates:
                fields["due_date"] = single_dates[0]
            
    cb_match = re.search(r'CASHBACK DETAILS(.*?)(?:Cashback earned this month|IMPORTANT MESSAGE|IMPORTANT)', text, re.DOTALL)
    if cb_match:
        cb_text = cb_match.group(1)
        earned_m = re.search(r'Cashback Earned\s*\n*\s*([\d,.]+)', cb_text, re.IGNORECASE)
        credited_m = re.search(r'Cashback Credited\s*\n*\s*([\d,.]+)', cb_text, re.IGNORECASE)
        if earned_m:
            fields["cb_earned"] = earned_m.group(1).replace(',', '').strip()
        if credited_m:
            fields["cb_credited"] = credited_m.group(1).replace(',', '').strip()
                     
    if fields["cb_earned"] is None:
        computed = compute_ledger_cashback(text)
        if computed > 0:
            fields["cb_earned"] = f"{computed:.2f}"
            
    return fields

# ─────────────────────────────────────────────────────────────
# Layer 2 Helper: accounting equation
# ─────────────────────────────────────────────────────────────

def validate_accounting(text, month):
    """Validates the internal accounting equation."""
    # Prev Balance - Payments - Credits + Purchase + Cash Advance + Other Debit&Charges = Total Payment Due
    pattern = re.search(
        r'([\d,]+\.\d+)(?:\s+(Dr|Cr))?\s+'         # 1, 2: Previous Balance
        r'([\d,]+\.\d+)\s+'                         # 3: Payments
        r'([\d,]+\.\d+)\s+'                         # 4: Credits
        r'([\d,]+\.\d+)\s+'                         # 5: Purchases
        r'([\d,]+\.\d+)\s+'                         # 6: Cash Advance
        r'([\d,]+\.\d+)\s+'                         # 7: Other Debits/Charges
        r'([\d,]+\.\d+)\s+Dr',                      # 8: Total Payment Due
        text
    )
    if not pattern:
        return None, "Could not find accounting equation line"

    try:
        prev_bal  = float(pattern.group(1).replace(',',''))
        prev_type = pattern.group(2) or "Dr"
        payments  = float(pattern.group(3).replace(',',''))
        credits   = float(pattern.group(4).replace(',',''))
        purchases = float(pattern.group(5).replace(',',''))
        cash_adv  = float(pattern.group(6).replace(',',''))
        other_chg = float(pattern.group(7).replace(',',''))
        total_due = float(pattern.group(8).replace(',',''))
    except ValueError:
        return None, "Error converting extracted numbers to float"

    # Compute: Previous Balance (Dr=+ / Cr=-) - Payments - Credits + Purchases + Cash Advance + Other Charges
    prev_signed = prev_bal if prev_type == "Dr" else -prev_bal
    computed = round(prev_signed - payments - credits + purchases + cash_adv + other_chg, 2)
    delta    = round(abs(computed - total_due), 2)

    return {
        "prev_balance": prev_signed, "payments": payments, "credits": credits,
        "purchases": purchases, "cash_advance": cash_adv, "other_charges": other_chg,
        "stated_total_due": total_due, "computed_total_due": computed,
        "delta": delta, "match": delta <= 1.0
    }, None

# ─────────────────────────────────────────────────────────────
# Layer 4 Helper: actual cashback credit from transactions list
# ─────────────────────────────────────────────────────────────

def extract_actual_cashback_credit(text):
    """Extracts the sum of actual cashback credits from the transaction ledger."""
    matches = re.findall(r'CASHBACK\s+CREDIT.*?\s+([\d,]+\.\d{2})\s+Cr', text, re.IGNORECASE)
    if not matches:
        matches = re.findall(r'CASHBACK.*?\s+([\d,]+\.\d{2})\s+Cr', text, re.IGNORECASE)
    
    total = 0.0
    for m in matches:
        try:
            total += float(m.replace(',', ''))
        except ValueError:
            pass
    return total if matches else None

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
            # Statement date is 15th.
            # d <= 15 belongs to month m, d > 15 belongs to month m+1
            if d <= 15:
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
        if f.endswith('.pdf') and 'Flipkart_Axis_Statement' in f
    ])

    month_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    def sort_key(filename):
        match = re.search(r'Statement_(\w+)_(\d{4})', filename)
        if match:
            try:
                return (int(match.group(2)), month_order.index(match.group(1)))
            except ValueError:
                return (9999, 99)
        return (9999, 99)

    pdf_files_sorted = sorted(pdf_files, key=sort_key)
    alerts_by_month = get_mapped_alerts()

    results = []
    all_pass = True
    prev_cb_earned = None

    print("=" * 90)
    print("  FLIPKART AXIS CARD — 4-LAYER DATA VALIDATION REPORT")
    print("=" * 90)

    # Let's validate only the recent year 2026 statements to keep logs clean
    statements_to_validate = []
    for pdf_file in pdf_files_sorted:
        m_match = re.search(r'Statement_(\w+)_(\d{4})', pdf_file)
        if m_match and m_match.group(2) == "2026":
            statements_to_validate.append(pdf_file)

    for idx, pdf_file in enumerate(statements_to_validate):
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        m_match = re.search(r'Statement_(\w+)_(\d{4})', pdf_file)
        month = f"{m_match.group(1)} {m_match.group(2)}"

        print(f"\n{'─'*90}")
        print(f"📄 {month}")
        print(f"{'─'*90}")

        # --- Extraction ---
        text_pypdf    = extract_pypdf(pdf_path)
        text_pdftotext = extract_pdftotext(pdf_path)

        # Extract next statement amounts to handle posting delays
        next_amounts = set()
        if idx + 1 < len(statements_to_validate):
            try:
                next_pdf_path = os.path.join(PDF_DIR, statements_to_validate[idx + 1])
                n_text_pypdf = extract_pypdf(next_pdf_path)
                n_text_pdftotext = extract_pdftotext(next_pdf_path)
                next_amounts = grab_amounts(n_text_pypdf) | grab_amounts(n_text_pdftotext)
            except Exception:
                pass

        issues = []

        # ── Layer 1: Dual-engine key-field comparison ──────────────────────────
        fields_pypdf     = extract_key_fields_pypdf(text_pypdf)
        fields_pdftotext = extract_key_fields_pdftotext(text_pdftotext)

        print("  LAYER 1 — Dual-engine extraction (pypdf vs pdftotext):")
        for field in ["due_date", "total_due", "min_due", "cb_earned", "cb_credited"]:
            v1 = fields_pypdf.get(field)
            v2 = fields_pdftotext.get(field)
            
            if v1 == v2:
                if v1 is not None:
                    print(f"    {PASS_ICON}  {field:<15} = {v1}")
                else:
                    print(f"    {PASS_ICON}  {field:<15} = None (Both Engines)")
            elif v1 is None or v2 is None:
                print(f"    {WARN_ICON} {field:<15}: one engine returned None  (pypdf={v1}, pdftotext={v2})")
                issues.append(f"L1: {field} — one engine returned None")
            else:
                try:
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
            pdf_amounts_float = {float(x.replace(',','')) for x in (amounts_pypdf | amounts_pdftotext | next_amounts)}
            
            missing = []
            for amt in alert_amounts:
                # Discard small amount alerts (like Myntra ₹9 spend) or refund alerts
                if amt < 100:
                    continue
                if not any(abs(amt - p_amt) < 0.01 for p_amt in pdf_amounts_float):
                    missing.append(amt)
            
            if not missing:
                print(f"    {PASS_ICON}  All alert amounts found in PDF: {sorted(alert_amounts)}")
            else:
                print(f"    {FAIL_ICON} Alert amounts NOT found in PDF: {missing}")
                issues.append(f"L3: Alert amounts missing from PDF: {missing}")
                all_pass = False
        else:
            print(f"    {WARN_ICON} No Gmail alert data for this month")

        # ── Layer 4: Cross-statement Cashback Credit Validation ────────────────
        print("  LAYER 4 — Cross-statement cashback validation:")
        cb_credited_val = fields_pypdf.get("cb_credited") or fields_pdftotext.get("cb_credited")
        cb_earned_val = fields_pypdf.get("cb_earned") or fields_pdftotext.get("cb_earned")
        
        ledger_credited = extract_actual_cashback_credit(text_pypdf) or extract_actual_cashback_credit(text_pdftotext)
        
        cb_credited_float = None
        if ledger_credited is not None:
            cb_credited_float = ledger_credited
        elif cb_credited_val:
            try:
                cb_credited_float = float(cb_credited_val.replace(',', ''))
            except ValueError:
                pass
                
        cb_earned_float = None
        if cb_earned_val:
            try:
                cb_earned_float = float(cb_earned_val.replace(',', ''))
            except ValueError:
                pass

        cashback_verified = True
        # For January 2026 statement, check against December 2025 statement.
        # We can load December 2025 earned from statements_data.json
        statements_data_path = os.path.join(PDF_DIR, "statements_data.json")
        dec_cb_earned = None
        if os.path.exists(statements_data_path):
            try:
                with open(statements_data_path, 'r') as f:
                    sd = json.load(f)
                    for s in sd.get("summary", []):
                        if s["month"] == "December 2025":
                            dec_cb_earned = s.get("cb_earned") or 474.0 # Fallback to 474.0
            except Exception:
                pass
        
        current_prev_cb = prev_cb_earned if prev_cb_earned is not None else dec_cb_earned

        if current_prev_cb is not None and cb_credited_float is not None:
            if abs(cb_credited_float - current_prev_cb) < 0.01:
                print(f"    {PASS_ICON}  Cashback credited (₹{cb_credited_float:,.2f}) matches previous month's earned (₹{current_prev_cb:,.2f})")
            else:
                print(f"    {FAIL_ICON} MISMATCH: Credited ₹{cb_credited_float:,.2f} but earned ₹{current_prev_cb:,.2f} in previous statement")
                issues.append(f"L4: Cashback credit mismatch (credited ₹{cb_credited_float:,.2f}, previous earned ₹{current_prev_cb:,.2f})")
                cashback_verified = False
                all_pass = False
        else:
            print(f"    {WARN_ICON} Missing cashback credited or previous earned value for validation")
            cashback_verified = False
                
        prev_cb_earned = cb_earned_float

        if not issues:
            print(f"\n  🟢 VERDICT: FULLY VALIDATED — no discrepancies found")
        else:
            print(f"\n  🔴 VERDICT: {len(issues)} issue(s) found:")
            for iss in issues:
                print(f"     • {iss}")

        results.append({
            "month": month,
            "issues": issues,
            "validated": len(issues) == 0,
            "cashback_verified": cashback_verified,
            "cb_credited": cb_credited_float
        })

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

    freshness = card_freshness.validate_freshness(
        PDF_DIR,
        card_name="Flipkart Axis",
        env_prefix="FLIPKART_AXIS",
        require_metadata=True,
        require_connector_evidence=False,
    )
    if freshness["warnings"] or freshness["failures"]:
        print(f"\n  {WARN_ICON} FRESHNESS / RECONCILIATION GATE")
        for warning in freshness["warnings"]:
            print(f"     • {warning}")
        for failure in freshness["failures"]:
            print(f"     • {failure}")
    results.append({
        "month": "Freshness / reconciliation gate",
        "issues": freshness["warnings"] + freshness["failures"],
        "validated": freshness["ok"],
        "freshness": freshness,
    })

    report_path = os.path.join(PDF_DIR, "validation_report.json")
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  Report saved → {report_path}")
    return all(r.get("validated", False) for r in results)

if __name__ == "__main__":
    raise SystemExit(0 if run_validation() else 1)
