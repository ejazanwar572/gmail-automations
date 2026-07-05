#!/usr/bin/env python3
"""
Sync latest transaction alerts from Gmail using official Google API.
Saves to gmail_alerts.json and triggers update_report.py.
"""

import os
import re
import json
import subprocess
import sys
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
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import card_freshness

def get_gmail_service():
    """Authenticates and returns the Gmail service object using active system credentials."""
    mcp_keys = "/Users/ejazanwar/.gmail-mcp/gcp-oauth.keys.json"
    mcp_token = "/Users/ejazanwar/.gmail-mcp/credentials.json"
    
    if os.path.exists(mcp_keys) and os.path.exists(mcp_token):
        try:
            with open(mcp_keys, 'r') as f:
                client_data = json.load(f)['installed']
            with open(mcp_token, 'r') as f:
                token_data = json.load(f)
                
            creds = Credentials(
                token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_data['client_id'],
                client_secret=client_data['client_secret'],
                scopes=token_data['scope'].split(' ')
            )
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_data['access_token'] = creds.token
                with open(mcp_token, 'w') as f:
                    json.dump(token_data, f)
            return build('gmail', 'v1', credentials=creds)
        except Exception as e:
            print(f"[!] Warning: Failed to load active Gmail MCP credentials: {e}")
            
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            pass
            
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        except Exception:
            creds = None
            
    if not creds:
        print("Could not load credentials.")
        return None
        
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
        message_ids = []
        print(f"Found {len(messages)} matching alert email(s). Extracting details...")
        
        for msg in messages:
            msg_id = msg['id']
            message_ids.append(msg_id)
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
            merchant_name = "Unknown"
            # Apply exact regex: Merchant Name:\s*\n*\s*([^\n]+)
            m_match = re.search(r'Merchant\s+Name:\s*\n*\s*([^\n]+)', body_text, re.IGNORECASE)
            if m_match:
                merchant_name = clean_html(m_match.group(1)).strip()
                merchant_name = re.sub(r'\s+', ' ', merchant_name)
            else:
                cleaned_body = clean_html(body_text)
                m_match_clean = re.search(r'Merchant\s+Name:\s*(.+?)\s*(?:Axis\s+Bank|Date\s*&|Transaction|$)', cleaned_body, re.IGNORECASE)
                if m_match_clean:
                    merchant_name = m_match_clean.group(1).strip()
                
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
                
            # Parse Amount from Subject (optional decimals)
            amount_match = re.search(r'INR\s*([\d,]+(?:\.\d{2})?)', subject, re.IGNORECASE)
            if not amount_match:
                amount_match = re.search(r'([\d,]+(?:\.\d{2})?)', subject)
                
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
        previous_count = len(card_freshness.load_alerts(SCRIPT_DIR))
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(parsed_alerts, f, indent=2)
        skipped_duplicate_count = max(0, len(messages) - len(card_freshness.unique_alerts(parsed_alerts)))
        card_freshness.write_sync_metadata(
            SCRIPT_DIR,
            card_name="Airtel Axis Credit Card",
            card_ending="3164",
            source="gmail-api",
            query='from:alerts@axis.bank.in spent on credit card no. XX3164',
            alerts=parsed_alerts,
            previous_count=previous_count,
            new_count=max(0, len(parsed_alerts) - previous_count),
            skipped_duplicate_count=skipped_duplicate_count,
            message_ids=message_ids,
        )
        print(f"Successfully saved {len(parsed_alerts)} alerts to: {OUTPUT_FILE}")
        print(f"Sync metadata saved → {os.path.join(SCRIPT_DIR, 'sync_metadata.json')}")
        
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
