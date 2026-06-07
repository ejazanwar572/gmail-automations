#!/usr/bin/env python3
"""
Sync latest SBI Cashback transaction alerts from Gmail using official Google API.
Saves to gmail_alerts.json and triggers update_report.py.
"""

import os
import re
import json
import subprocess
from datetime import datetime
from email.utils import parsedate_to_datetime

# Google OAuth & API Libraries
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("=========================================================================")
    print("Missing dependencies! Please run:")
    print("  pip install google-auth-oauthlib google-api-python-client")
    print("=========================================================================")
    exit(1)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'gmail_alerts.json')
REPORT_SCRIPT = os.path.join(SCRIPT_DIR, 'update_report.py')

def get_gmail_service():
    """Authenticates and returns the Gmail service object."""
    global CREDENTIALS_FILE, TOKEN_FILE
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            pass
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
                
        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                # Fallback to check parent directory for credentials
                parent_creds = os.path.join(os.path.dirname(SCRIPT_DIR), 'Airtel Axis Statements', 'credentials.json')
                parent_token = os.path.join(os.path.dirname(SCRIPT_DIR), 'Airtel Axis Statements', 'token.json')
                if os.path.exists(parent_creds):
                    CREDENTIALS_FILE = parent_creds
                if os.path.exists(parent_token):
                    TOKEN_FILE = parent_token
                    try:
                        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
                        if creds and creds.valid:
                            return build('gmail', 'v1', credentials=creds)
                    except Exception:
                        pass
            
            if not creds and not os.path.exists(CREDENTIALS_FILE):
                print("=========================================================================")
                print("                    GOOGLE CREDENTIALS FILE NOT FOUND                    ")
                print("=========================================================================")
                print(f"Please place your downloaded 'credentials.json' in: \n  {CREDENTIALS_FILE}\n")
                print("=========================================================================")
                return None
            
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build('gmail', 'v1', credentials=creds)

def get_message_body(payload):
    """Recursively extracts the text body from the message payload."""
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            mime_type = part.get('mimeType', '')
            if mime_type in ['text/plain', 'text/html']:
                data = part.get('body', {}).get('data')
                if data:
                    import base64
                    body += base64.urlsafe_b64decode(data.encode('utf-8')).decode('utf-8', errors='ignore')
            elif 'parts' in part:
                body += get_message_body(part)
    else:
        data = payload.get('body', {}).get('data')
        if data:
            import base64
            body = base64.urlsafe_b64decode(data.encode('utf-8')).decode('utf-8', errors='ignore')
    return body

def clean_html(html_text):
    """Strips HTML tags and normalizes whitespace."""
    text = re.sub(r'<[^>]+>', ' ', html_text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def main():
    service = get_gmail_service()
    if not service:
        return
        
    print("Searching Gmail for SBI Cashback Card transaction alerts...")
    query = 'from:onlinesbicard@sbicard.com subject:"Transaction Alert from CASHBACK SBI Card" "ending 0846"'
    
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=100).execute()
        messages = results.get('messages', [])
        
        parsed_alerts = []
        print(f"Found {len(messages)} matching alert email(s). Extracting details...")
        
        for msg in messages:
            msg_id = msg['id']
            msg_details = service.users().messages().get(
                userId='me', 
                id=msg_id, 
                format='full'
            ).execute()
            
            payload = msg_details.get('payload', {})
            subject = ""
            date_header = ""
            for header in payload.get('headers', []):
                if header['name'] == 'Subject':
                    subject = header['value']
                elif header['name'] == 'Date':
                    date_header = header['value']
            
            body_text = get_message_body(payload)
            cleaned_body = clean_html(body_text)
            
            # Match: Rs.1,304.00 spent on your SBI Credit Card ending 0846 at ASSPL on 03/06/26.
            match = re.search(
                r'Rs\.([\d,]+\.\d{2})\s+spent on your SBI Credit Card ending 0846 at (.*?)\s+on\s+(\d{2}/\d{2}/\d{2})',
                cleaned_body,
                re.IGNORECASE
            )
            
            if match:
                amount = float(match.group(1).replace(',', ''))
                merchant_name = match.group(2).strip()
                date_str = match.group(3).strip()
                
                # Convert date format from DD/MM/YY to DD/MM/YYYY
                try:
                    d, m, y = date_str.split('/')
                    date_formatted = f"{d}/{m}/20{y}"
                except Exception:
                    # Fallback to Date header
                    try:
                        dt = parsedate_to_datetime(date_header)
                        date_formatted = dt.strftime("%d/%m/%Y")
                    except Exception:
                        continue
                
                subject_with_merchant = f"Transaction Alert from CASHBACK SBI Card at {merchant_name}"
                parsed_alerts.append({
                    "subject": subject_with_merchant,
                    "date": date_formatted,
                    "amount": amount
                })
                print(f"  Parsed: {date_formatted} | ₹{amount:.2f} | {merchant_name}")
            else:
                # Alternate search format check
                amount_match = re.search(r'Rs\.([\d,]+\.\d{2})', cleaned_body)
                if amount_match:
                    amount = float(amount_match.group(1).replace(',', ''))
                    # Fallback Date parsing
                    try:
                        dt = parsedate_to_datetime(date_header)
                        date_formatted = dt.strftime("%d/%m/%Y")
                    except Exception:
                        continue
                    subject_with_merchant = f"Transaction Alert from CASHBACK SBI Card at Unknown"
                    parsed_alerts.append({
                        "subject": subject_with_merchant,
                        "date": date_formatted,
                        "amount": amount
                    })
                    print(f"  Parsed (Partial): {date_formatted} | ₹{amount:.2f} | Unknown")
                else:
                    print(f"  Skipped (could not parse transaction): {subject}")
                
        # Write to JSON
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(parsed_alerts, f, indent=2)
        print(f"Successfully saved {len(parsed_alerts)} alerts to: {OUTPUT_FILE}")
        
        # Run report update script
        if os.path.exists(REPORT_SCRIPT):
            print("Running report update script...")
            result = subprocess.run(['python3', REPORT_SCRIPT], capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(f"Error updating report:\n{result.stderr}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
