#!/usr/bin/env python3
"""
Sync latest transaction alerts from Gmail using official Google API.
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
                print("=========================================================================")
                print("                    GOOGLE CREDENTIALS FILE NOT FOUND                    ")
                print("=========================================================================")
                print(f"Please place your downloaded 'credentials.json' in: \n  {CREDENTIALS_FILE}\n")
                print("How to get credentials.json:")
                print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
                print("2. Create a Project, go to 'APIs & Services' -> 'Library', and enable 'Gmail API'.")
                print("3. Go to 'OAuth consent screen', configure it, and add your email as a test user.")
                print("4. Go to 'Credentials' -> 'Create Credentials' -> 'OAuth client ID'.")
                print("5. Select Application Type: 'Desktop app', name it, click Create.")
                print("6. Download the JSON file, rename it to 'credentials.json', and save it in the folder.")
                print("=========================================================================")
                return None
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
        
    print("Searching Gmail for Axis Card transaction alerts...")
    query = "from:alerts@axis.bank.in spent on credit card no. XX3164"
    
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=100).execute()
        messages = results.get('messages', [])
        
        parsed_alerts = []
        print(f"Found {len(messages)} matching alert email(s). Extracting details...")
        
        for msg in messages:
            msg_id = msg['id']
            # Fetch full message payload to extract merchant name from body
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
            
            # Extract body text and get merchant name
            body_text = get_message_body(payload)
            cleaned_body = clean_html(body_text)
            merchant_name = "Unknown"
            merchant_match = re.search(r'Merchant\s+Name:\s*(.+?)\s*(?:Axis\s+Bank|Date\s*&|Transaction|$)', cleaned_body, re.IGNORECASE)
            if merchant_match:
                merchant_name = merchant_match.group(1).strip()
                
            # Append merchant name to subject to support downstream categorization
            if merchant_name != "Unknown" and merchant_name not in subject:
                subject_with_merchant = f"{subject} at {merchant_name}"
            else:
                subject_with_merchant = subject

            # Parse Date (RFC 2822) to DD/MM/YYYY
            try:
                dt = parsedate_to_datetime(date_header)
                date_formatted = dt.strftime("%d/%m/%Y")
            except Exception as e:
                print(f"Error parsing Date header '{date_header}': {e}")
                continue
                
            # Parse Amount from Subject (e.g. "INR 714.44 spent on credit card no. XX3164")
            amount_match = re.search(r'INR\s*([\d,]+\.\d{2})', subject, re.IGNORECASE)
            if not amount_match:
                amount_match = re.search(r'([\d,]+\.\d{2})', subject)
                
            if amount_match:
                amount = float(amount_match.group(1).replace(',', ''))
                parsed_alerts.append({
                    "subject": subject_with_merchant,
                    "date": date_formatted,
                    "amount": amount
                })
                print(f"  Parsed: {date_formatted} | ₹{amount:.2f} | {subject_with_merchant}")
            else:
                print(f"  Skipped (could not parse amount): {subject}")
                
        # Write to JSON
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(parsed_alerts, f, indent=2)
        print(f"Successfully saved {len(parsed_alerts)} alerts to: {OUTPUT_FILE}")
        
        # Run report update script
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
