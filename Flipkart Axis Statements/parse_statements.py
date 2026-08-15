#!/usr/bin/env python3
"""
Parse all Flipkart Axis Bank Credit Card statement PDFs.
"""

import os
import re
import json
from pypdf import PdfReader

PDF_DIR = "/Users/ejazanwar/Documents/Gmail Automations/Flipkart Axis Statements"
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

PASSWORD = get_env_password("AIRTEL_AXIS_PASSWORD", PASSWORD) # Reuse password env if set
OUTPUT_FILE = os.path.join(PDF_DIR, "statements_data.json")

def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        reader.decrypt(PASSWORD)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def parse(text, filename):
    month_match = re.search(r'Statement_(\w+)_(\d{4})\.pdf', filename)
    month = f"{month_match.group(1)} {month_match.group(2)}" if month_match else filename

    # --- Summary fields ---
    payment_summary = re.search(
        r'(\d{2}/\d{2}/\d{4})\s*-\s*\d{2}/\d{2}/\d{4}\s+'
        r'(\d{2}/\d{2}/\d{4})\s+'
        r'\d{2}/\d{2}/\d{4}'
        r'([\d,]+\.\d+)\s*Dr\s+([\d,]+\.\d+)\s*Dr',
        text
    )
    stmt_date    = payment_summary.group(1) if payment_summary else None
    due_date     = payment_summary.group(2) if payment_summary else None
    total_due    = payment_summary.group(3).replace(',','') if payment_summary else None
    min_due      = payment_summary.group(4).replace(',','') if payment_summary else None

    # Credit card number line: CardNo CreditLimit AvailCredit AvailCash
    credit_line = re.search(
        r'533467\*+\d{4}\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)',
        text
    )
    credit_limit = credit_line.group(1).replace(',','') if credit_line else None
    avail_credit = credit_line.group(2).replace(',','') if credit_line else None

    # --- Cashback Details section ---
    cb_section = re.search(r'CASHBACK DETAILS.*?Cashback Earned\s+Cashback Credited\s+([\d,.]+)\s+([\d,.]+)', text, re.DOTALL)
    cb_earned   = float(cb_section.group(1).replace(',','')) if cb_section else None
    cb_credited = float(cb_section.group(2).replace(',','')) if cb_section else None

    # --- Transactions: DD/MM/YYYY Description Amount Dr/Cr Cashback Amount Dr/Cr ---
    # Example: 22/04/2026 FLIPKART PAYMENTS,GURGAON MISC STORE 288.00 Dr 14.00 Cr
    tx_pattern = re.compile(
        r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s+(Dr|Cr)(?:\s+([\d,]+\.\d{2})\s+(Dr|Cr))?',
        re.MULTILINE
    )
    transactions = []
    for m in tx_pattern.finditer(text):
        groups = m.groups()
        date, desc, amount, dr_cr = groups[0], groups[1], groups[2], groups[3]
        cb_amt = float(groups[4].replace(',', '')) if groups[4] else 0.0
        cb_type = groups[5] if groups[5] else 'Cr'
        
        transactions.append({
            "date": date,
            "description": desc.strip(),
            "amount": float(amount.replace(',', '')),
            "type": dr_cr,
            "cashback_earned": cb_amt,
            "cashback_type": cb_type
        })

    # Filter out EMI Balances or Card No header matching patterns
    clean_txns = []
    for t in transactions:
        desc_upper = t["description"].upper()
        if "CARD NO:" in desc_upper or "EMI BALANCES" in desc_upper or "PAGE :" in desc_upper:
            continue
        clean_txns.append(t)
    transactions = clean_txns

    # --- Cashback transaction lines ---
    cashback_txns = [t for t in transactions if 'CASHBACK' in t['description'].upper()]

    # --- Spending by category ---
    categories = {}
    for t in transactions:
        if t['type'] == 'Dr':
            cat_match = re.search(r'\b(UTILITIES|ELECTRONICS|TELECOM|GROCERY|DINING|FUEL|TRAVEL|ENTERTAINMENT|INSURANCE|OTHERS)\b', t['description'].upper())
            cat = cat_match.group(1) if cat_match else 'OTHER'
            categories[cat] = categories.get(cat, 0) + t['amount']

    total_spends  = sum(t['amount'] for t in transactions if t['type'] == 'Dr')
    total_credits = sum(t['amount'] for t in transactions if t['type'] == 'Cr')

    return {
        "month": month,
        "filename": filename,
        "statement_date": stmt_date,
        "due_date": due_date,
        "total_amount_due": float(total_due) if total_due else None,
        "minimum_amount_due": float(min_due) if min_due else None,
        "credit_limit": float(credit_limit) if credit_limit else None,
        "available_credit": float(avail_credit) if avail_credit else None,
        "cashback_earned": cb_earned,
        "cashback_credited": cb_credited,
        "total_debits": round(total_spends, 2),
        "total_credits": round(total_credits, 2),
        "category_spend": {k: round(v, 2) for k, v in sorted(categories.items(), key=lambda x: -x[1])},
        "cashback_transactions": cashback_txns,
        "transactions": transactions,
        "transaction_count": len(transactions),
    }

def main():
    pdf_files = sorted([f for f in os.listdir(PDF_DIR) if f.endswith('.pdf') and 'Flipkart_Axis_Statement' in f])
    
    # Sort files chronologically
    month_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    def get_sort_key(filename):
        m = re.search(r'Statement_(\w+)_(\d{4})', filename)
        if m:
            return (int(m.group(2)), month_order.index(m.group(1)))
        return (0, 0)
    pdf_files_sorted = sorted(pdf_files, key=get_sort_key)
    
    print(f"Processing {len(pdf_files_sorted)} statements...\n")

    all_data = []
    summary_table = []

    for pdf_file in pdf_files_sorted:
        text = extract_text(os.path.join(PDF_DIR, pdf_file))
        data = parse(text, pdf_file)
        all_data.append(data)

        summary_table.append({
            "month": data["month"],
            "total_due": data["total_amount_due"],
            "due_date": data["due_date"],
            "debits": data["total_debits"],
            "credits": data["total_credits"],
            "cb_earned": data["cashback_earned"],
            "cb_credited": data["cashback_credited"],
            "txn_count": data["transaction_count"],
        })

        print(f"📅 {data['month']:<20} | Due: ₹{str(data['total_amount_due']):<10} | "
              f"Spends: ₹{str(data['total_debits']):<10} | "
              f"CB Earned: ₹{str(data['cashback_earned']):<8} | "
              f"CB Credited: ₹{str(data['cashback_credited']):<8} | "
              f"Txns: {data['transaction_count']}")

    # Totals
    print("\n" + "="*110)
    total_cb_earned   = sum(r["cb_earned"]   or 0 for r in summary_table)
    total_cb_credited = sum(r["cb_credited"] or 0 for r in summary_table)
    total_spends      = sum(r["debits"]      or 0 for r in summary_table)
    print(f"TOTALS ({len(summary_table)} months): Spends=₹{total_spends:,.2f} | CB Earned=₹{total_cb_earned:,.2f} | CB Credited=₹{total_cb_credited:,.2f}")

    with open(OUTPUT_FILE, 'w') as f:
        json.dump({"summary": summary_table, "statements": all_data}, f, indent=2)

    print(f"\n✅ Data saved → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
