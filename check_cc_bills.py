#!/usr/bin/env python3
"""
Credit Card Bill Payment Tracker:
1. Parses Airtel Axis, Flipkart Axis, and SBI Cashback statement PDFs.
2. Parses CRED bill generation emails in Gmail to support any number of credit cards dynamically.
3. Reconciles bill info with repayment confirmation emails.
4. Outputs payment status and outstanding balances to JSON.
"""

import os
import re
import json
import subprocess
import argparse
from datetime import datetime, timezone
from pypdf import PdfReader
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE_DIR = "/Users/ejazanwar/Documents/Gmail Automations"
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
OUTPUT_STATUS_FILE = "/tmp/cc_bills_status.json"

# Default passwords
SBI_PASSWORD_DEFAULT = "281219950846"
AXIS_PASSWORD_DEFAULT = "MDEJ2812"

def get_env_password(var_name, default=""):
    """Loads password from env or root .env file."""
    val = os.environ.get(var_name)
    if val:
        return val
    env_path = os.path.join(BASE_DIR, ".env")
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
    return default

SBI_PASSWORD = get_env_password("SBI_CASHBACK_PASSWORD", SBI_PASSWORD_DEFAULT)
AXIS_PASSWORD = get_env_password("AIRTEL_AXIS_PASSWORD", AXIS_PASSWORD_DEFAULT)

def extract_pdf_text_pypdf(pdf_path, password):
    """Extracts text using PyPDF."""
    try:
        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            reader.decrypt(password)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        print(f"[PDF Extraction] PyPDF failed for {os.path.basename(pdf_path)}: {e}")
        return ""

def extract_pdf_text_pdftotext(pdf_path, password):
    """Extracts text using pdftotext CLI."""
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/pdftotext", "-layout", "-upw", password, pdf_path, "-"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return result.stdout
        
        result = subprocess.run(
            ["/opt/homebrew/bin/pdftotext", "-layout", "-opw", password, pdf_path, "-"],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout
    except Exception as e:
        print(f"[PDF Extraction] pdftotext failed for {os.path.basename(pdf_path)}: {e}")
        return ""

def get_latest_statement_pdf(directory, prefix):
    """Scans directory and returns the path to the latest statement PDF."""
    if not os.path.exists(directory):
        return None
    pdf_files = [
        f for f in os.listdir(directory)
        if f.endswith('.pdf') and prefix in f
    ]
    if not pdf_files:
        return None
    
    month_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    def sort_key(filename):
        match = re.search(rf'{prefix}_(\w+)_(\d{{4}})', filename, re.IGNORECASE)
        if match:
            m_str = match.group(1).lower()
            y_str = match.group(2)
            return (int(y_str), month_map.get(m_str, 0))
        return (0, 0)
    
    pdf_files.sort(key=sort_key, reverse=True)
    return os.path.join(directory, pdf_files[0])

def parse_axis_statement(pdf_path):
    """Parses Axis statement PDF (Airtel or Flipkart)."""
    text = extract_pdf_text_pypdf(pdf_path, AXIS_PASSWORD)
    payment_summary = re.search(
        r'(\d{2}/\d{2}/\d{4})\s*-\s*\d{2}/\d{2}/\d{4}\s+'
        r'(\d{2}/\d{2}/\d{4})\s+\d{2}/\d{2}/\d{4}'
        r'([\d,]+\.\d+)\s*Dr\s+([\d,]+\.\d+)\s*Dr',
        text
    )
    if payment_summary:
        return {
            "statement_date": payment_summary.group(1),
            "due_date": payment_summary.group(2),
            "total_due": float(payment_summary.group(3).replace(',', '')),
            "min_due": float(payment_summary.group(4).replace(',', ''))
        }
        
    text_pdftotext = extract_pdf_text_pdftotext(pdf_path, AXIS_PASSWORD)
    summary_match = re.search(r'PAYMENT SUMMARY(.*?)Credit Card Number', text_pdftotext, re.DOTALL)
    if summary_match:
        lines = [line.strip() for line in summary_match.group(1).split('\n') if line.strip()]
        if len(lines) >= 8:
            try:
                total_due = float(lines[4].replace('Dr', '').replace('Cr', '').replace(',', '').strip())
                min_due = float(lines[5].replace('Dr', '').replace('Cr', '').replace(',', '').strip())
                due_date = lines[7].strip()
                period_match = re.search(r'(\d{2}/\d{2}/\d{4})\s*-\s*\d{2}/\d{2}/\d{4}', text_pdftotext)
                statement_date = period_match.group(1) if period_match else None
                return {
                    "statement_date": statement_date,
                    "due_date": due_date,
                    "total_due": total_due,
                    "min_due": min_due
                }
            except Exception:
                pass
    return None

def parse_sbi_statement(pdf_path):
    """Parses SBI Cashback statement PDF."""
    text = extract_pdf_text_pdftotext(pdf_path, SBI_PASSWORD)
    dates = re.findall(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', text)
    statement_date = dates[0] if len(dates) >= 1 else None
    due_date = dates[1] if len(dates) >= 2 else None
    
    def format_sbi_date(d_str):
        if not d_str:
            return None
        try:
            dt = datetime.strptime(d_str, "%d %b %Y")
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            return d_str
            
    statement_date = format_sbi_date(statement_date)
    due_date = format_sbi_date(due_date)
    
    total_due = None
    total_due_match = re.search(r'\*Total Amount Due[^\n]*\n+\s*([\d,]+\.\d{2})', text)
    if total_due_match:
        total_due = float(total_due_match.group(1).replace(",", "").strip())
        
    min_due = None
    min_due_match = re.search(r'\*\*Minimum Amount Due\s*\([^\)]*\)\s*\n+(?:[^\n]*\n)?\s*([\d,]+\.\d{2})', text)
    if min_due_match:
        min_due = float(min_due_match.group(1).replace(",", "").strip())
        
    if total_due is None:
        summary_pos = text.find("ACCOUNT SUMMARY")
        if summary_pos != -1:
            summary_text = text[summary_pos:summary_pos+1000]
            summary_row = re.search(r'([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})', summary_text)
            if summary_row:
                total_due = float(summary_row.group(5).replace(",", "").strip())
                min_due = float(summary_row.group(4).replace(",", "").strip())
                
    if total_due is not None:
        return {
            "statement_date": statement_date,
            "due_date": due_date,
            "total_due": total_due,
            "min_due": min_due
        }
    return None

def get_gmail_service():
    """Builds and returns the Gmail API service, handling OAuth token refresh."""
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError("Gmail OAuth token.json not found. Reauthentication required.")
        
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes=["https://www.googleapis.com/auth/gmail.readonly"])
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())
        except Exception as e:
            raise RuntimeError(f"Failed to refresh OAuth token: {e}")
    return build('gmail', 'v1', credentials=creds)

def format_date_str(d_str):
    """Formats raw date strings into DD/MM/YYYY format."""
    if not d_str:
        return None
    d_str_clean = re.sub(r'\s+', ' ', d_str).strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %b %Y", "%d %B %Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(d_str_clean, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            pass
    return d_str_clean

def parse_cred_bill_email(body, subject):
    """Parses CRED new bill alert email body and subject."""
    body_clean = re.sub(r'\s+', ' ', body)
    
    # Extract card digits
    card_match = re.search(r'(?:••••|XXXX-|card\s+XXXX-)\s*(\d{4})', body_clean, re.IGNORECASE)
    if not card_match:
        card_match = re.search(r'(?:••••|XXXX-|card\s+XXXX-)\s*(\d{4})', subject, re.IGNORECASE)
    if not card_match:
        return None
    card_digits = card_match.group(1)
    
    # Extract issuer
    issuer_match = re.search(r'([A-Za-z\s]+)\s*(?:••••|XXXX-|card\s+XXXX-)\s*' + card_digits, body_clean, re.IGNORECASE)
    if not issuer_match:
        issuer_match = re.search(r'([A-Za-z\s]+)\s*(?:••••|XXXX-|card\s+XXXX-)\s*' + card_digits, subject, re.IGNORECASE)
    issuer = issuer_match.group(1).strip() if issuer_match else "Unknown Card"
    
    # Clean issuer prefix
    if "generated" in issuer.lower():
        parts = re.split(r'generated\s+', issuer, flags=re.IGNORECASE)
        if len(parts) >= 2:
            issuer = parts[-1].strip()
            
    # Extract total due
    total_due = None
    total_due_match = re.search(r'total amount due ₹\s*([\d,]+\.?\d*)', body_clean, re.IGNORECASE)
    if not total_due_match:
        total_due_match = re.search(r'amount due ₹\s*([\d,]+\.?\d*)', body_clean, re.IGNORECASE)
    if total_due_match:
        total_due = float(total_due_match.group(1).replace(',', ''))
        
    # Extract min due
    min_due = 0.0
    min_due_match = re.search(r'minimum due ₹\s*([\d,]+\.?\d*)', body_clean, re.IGNORECASE)
    if min_due_match:
        min_due = float(min_due_match.group(1).replace(',', ''))
        
    # Extract due date
    due_date = None
    due_date_match = re.search(r'due date\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', body_clean, re.IGNORECASE)
    if due_date_match:
        due_date = format_date_str(due_date_match.group(1).strip())
        
    # Extract bill month
    month_match = re.search(r'bill for\s+(\w+)\s+has been generated', body_clean, re.IGNORECASE)
    statement_month = month_match.group(1).strip().capitalize() if month_match else "Unknown"
    
    # Standardize statement_month with year
    if statement_month != "Unknown" and due_date and len(due_date) >= 4:
        statement_month = f"{statement_month} {due_date[-4:]}"
    
    # Extract bill generated date
    gen_date = None
    gen_date_match = re.search(r'bill generated on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', body_clean, re.IGNORECASE)
    if gen_date_match:
        gen_date = format_date_str(gen_date_match.group(1).strip())
        
    if total_due is not None:
        return {
            "card_name": issuer,
            "card_digits": card_digits,
            "statement_month": statement_month,
            "total_due": total_due,
            "min_due": min_due,
            "due_date": due_date,
            "statement_date": gen_date
        }
    return None

def fetch_cred_bills_from_gmail(service, start_date_str):
    """Searches and parses CRED bill alerts since start_date_str."""
    query = f'from:protect@cred.club ("Important : New bill for your" OR "Important : New smart statement for your") after:{start_date_str}'
    results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
    messages = results.get('messages', [])
    
    cards_map = {}
    for msg in messages:
        msg_id = msg['id']
        meta = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        
        # Extract subject and body
        headers = meta.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
        snippet = meta.get('snippet', '')
        
        parsed = parse_cred_bill_email(snippet, subject)
        if parsed:
            digits = parsed["card_digits"]
            # Keep the newest bill if duplicates exist for the same card ending
            existing = cards_map.get(digits)
            if not existing:
                cards_map[digits] = parsed
            else:
                # Compare due dates or month to keep the latest
                try:
                    dt_new = datetime.strptime(parsed["due_date"], "%d/%m/%Y")
                    dt_old = datetime.strptime(existing["due_date"], "%d/%m/%Y")
                    if dt_new > dt_old:
                        cards_map[digits] = parsed
                except Exception:
                    pass
    return list(cards_map.values())

def search_payments_in_gmail(service, start_date_str):
    """Searches Gmail for payment confirmations."""
    query = f'subject:("payment received" OR "payment successful" OR "thank you for payment" OR "credited" OR "acknowledgement" OR "payment was successful" OR "payment confirmation") after:{start_date_str}'
    results = service.users().messages().list(userId='me', q=query, maxResults=100).execute()
    messages = results.get('messages', [])
    
    parsed_payments = []
    for msg in messages:
        msg_id = msg['id']
        msg_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        
        # Extract headers
        headers = msg_data.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
        date_raw = msg_data.get('internalDate', '')
        
        # Convert internal epoch date to string
        try:
            email_dt = datetime.fromtimestamp(int(date_raw) / 1000.0, tz=timezone.utc)
            date_formatted = email_dt.strftime("%d/%m/%Y")
        except Exception:
            date_formatted = ""
            
        snippet = msg_data.get('snippet', '')
        
        parsed_payments.append({
            "id": msg_id,
            "sender": sender,
            "subject": subject,
            "date": date_formatted,
            "body": snippet
        })
    return parsed_payments

def extract_payments_for_card(payments_list, card_digits, statement_date_str):
    """Parses payment emails to sum up payments made since statement_date."""
    stmt_dt = datetime.strptime(statement_date_str, "%d/%m/%Y")
    matched_payments = []
    
    # Check for card ending
    # Match both standard digits and CRED dot pattern (e.g. •••• 3164)
    card_pat = re.compile(rf'(?:••••|XXXX-|\b){card_digits}\b')
    amt_pat = re.compile(r'(?:Rs\.?|INR|₹)\s*([\d,]+\.?\d*)', re.IGNORECASE)
    
    for pay in payments_list:
        full_text = f"{pay['subject']} {pay['body']}"
        if not card_pat.search(full_text):
            continue
            
        # Verify payment date is after statement date
        try:
            email_dt = datetime.strptime(pay["date"], "%d/%m/%Y")
            if email_dt < stmt_dt:
                continue
        except Exception:
            pass
            
        # Parse the payment amount
        amounts = []
        for match in amt_pat.finditer(full_text):
            try:
                amt_val = float(match.group(1).replace(',', ''))
                amounts.append(amt_val)
            except ValueError:
                pass
                
        if amounts:
            valid_amounts = [a for a in amounts if a < 500000.0]
            if valid_amounts:
                amt = max(valid_amounts)
                matched_payments.append({
                    "amount": amt,
                    "date": pay["date"],
                    "subject": pay["subject"],
                    "sender": pay["sender"]
                })
    return matched_payments

def main():
    parser = argparse.ArgumentParser(description="Multi-card bill tracker.")
    parser.add_argument("--dry-run", action="store_true", help="Statement parsing only.")
    args = parser.parse_args()

    print("=== Credit Card Bill Tracker ===")
    
    results_map = {}
    authenticated = True
    auth_error = None
    
    # Setup Gmail service if possible
    service = None
    if not args.dry_run:
        try:
            service = get_gmail_service()
        except Exception as e:
            authenticated = False
            auth_error = str(e)
            print(f"[ERROR] Gmail authentication failed: {e}")
            
    # 1. Fetch statements from CRED emails in Gmail
    if service:
        print("\nQuerying Gmail for CRED bill alerts...")
        # Search last 45 days of bills
        cred_cards = fetch_cred_bills_from_gmail(service, "2026-05-01")
        for card in cred_cards:
            digits = card["card_digits"]
            results_map[digits] = card
            print(f"Found bill for {card['card_name']} ({digits}): ₹{card['total_due']:.2f} due by {card['due_date']}")

    # 2. Parse and merge local PDF statements (override or append)
    print("\nProcessing local PDF statements...")
    local_configs = [
        {
            "name": "Airtel Axis",
            "digits": "3164",
            "dir": os.path.join(BASE_DIR, "Airtel Axis Statements"),
            "prefix": "Airtel_Axis_Statement",
            "parser": parse_axis_statement
        },
        {
            "name": "Flipkart Axis",
            "digits": "6969",
            "dir": os.path.join(BASE_DIR, "Flipkart Axis Statements"),
            "prefix": "Flipkart_Axis_Statement",
            "parser": parse_axis_statement
        },
        {
            "name": "SBI Cashback",
            "digits": "0846",
            "dir": os.path.join(BASE_DIR, "SBI Cashback Statements"),
            "prefix": "SBI_Cashback_Statement",
            "parser": parse_sbi_statement
        }
    ]
    
    for c in local_configs:
        pdf_path = get_latest_statement_pdf(c["dir"], c["prefix"])
        if pdf_path:
            stmt = c["parser"](pdf_path)
            if stmt:
                digits = c["digits"]
                
                # Check statement month
                match = re.search(rf'{c["prefix"]}_(\w+)_(\d{{4}})', os.path.basename(pdf_path))
                month_str = f"{match.group(1)} {match.group(2)}" if match else "Unknown"
                
                pdf_data = {
                    "card_name": c["name"],
                    "card_digits": digits,
                    "statement_month": month_str,
                    "total_due": stmt["total_due"],
                    "min_due": stmt["min_due"],
                    "due_date": stmt["due_date"],
                    "statement_date": stmt["statement_date"],
                    "pdf_filename": os.path.basename(pdf_path)
                }
                
                # Merge: PDF statement overrides CRED alert if it exists
                results_map[digits] = pdf_data
                print(f"Loaded/Merged PDF for {c['name']} ({digits}): ₹{stmt['total_due']:.2f} due by {stmt['due_date']}")

    results = list(results_map.values())
    
    # 3. Fetch repayments and reconcile
    if not args.dry_run and service:
        # Search payments from 2026-04-01 to capture current cycle
        print("\nQuerying Gmail for payment confirmations...")
        payments = search_payments_in_gmail(service, "2026-04-01")
        print(f"Found {len(payments)} potential payment confirmation emails.")
        
        for r in results:
            card_payments = extract_payments_for_card(payments, r["card_digits"], r["statement_date"])
            total_paid = sum(p["amount"] for p in card_payments)
            
            outstanding = round(max(0.0, r["total_due"] - total_paid), 2)
            
            if outstanding == 0.0:
                status = "Paid ✅"
            elif total_paid > 0.0:
                status = "Partially Paid ⚠️"
            else:
                status = "Unpaid ❌"
                
            r["payment_status"] = status
            r["payments_found"] = card_payments
            r["total_paid"] = total_paid
            r["outstanding_due"] = outstanding
            
            print(f"  {r['card_name']} ({r['card_digits']}) Status: {status} | Due: ₹{r['total_due']:.2f} | Paid: ₹{total_paid:.2f} | Outstanding: ₹{outstanding:.2f}")
    else:
        # Dry run / Auth fail placeholder
        for r in results:
            r["payment_status"] = "Unknown (Dry Run)" if args.dry_run else "Unknown (Auth Fail)"
            r["payments_found"] = []
            r["total_paid"] = 0.0
            r["outstanding_due"] = r["total_due"]
            
    # 4. Write status output
    output_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authenticated": authenticated,
        "auth_error": auth_error,
        "cards": results
    }
    
    with open(OUTPUT_STATUS_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"\nPayment status written to {OUTPUT_STATUS_FILE}")

if __name__ == "__main__":
    main()
