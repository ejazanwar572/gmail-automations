#!/usr/bin/env python3
import os
import re
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')

def get_gmail_service():
    # Attempt to load credentials from the local Gmail MCP configuration folder
    mcp_keys = "/Users/ejazanwar/.gmail-mcp/gcp-oauth.keys.json"
    mcp_token = "/Users/ejazanwar/.gmail-mcp/credentials.json"
    
    if os.path.exists(mcp_keys) and os.path.exists(mcp_token):
        try:
            import json
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
            # Try refreshing if expired
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
        except Exception as e:
            print(f"Error loading TOKEN_FILE: {e}")
            pass
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"Error refreshing token: {e}")
            creds = None
    if not creds:
        print("Could not load credentials.")
        return None
    return build('gmail', 'v1', credentials=creds)

def download_statements():
    service = get_gmail_service()
    if not service:
        print("Failed to authenticate.")
        return
        
    print("Searching for Flipkart Axis statement emails...")
    query = '"Flipkart Axis Bank Credit Card Statement ending XX69"'
    results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
    messages = results.get('messages', [])
    
    print(f"Found {len(messages)} statement emails. Downloading attachments...")
    for msg in messages:
        msg_id = msg['id']
        msg_details = service.users().messages().get(userId='me', id=msg_id).execute()
        
        subject = ""
        for header in msg_details.get('payload', {}).get('headers', []):
            if header['name'] == 'Subject':
                subject = header['value']
                break
                
        # Parse month and year from subject
        # Example: "Flipkart Axis Bank Credit Card Statement ending XX69 - January 2026"
        month_match = re.search(r'Statement ending XX69 - (\w+ \d{4})', subject, re.IGNORECASE)
        if not month_match:
            print(f"Skipping subject: {subject} (could not parse month/year)")
            continue
            
        month_year_str = month_match.group(1) # e.g. "January 2026"
        month_name, year = month_year_str.split()
        
        filename = f"Flipkart_Axis_Statement_{month_name}_{year}.pdf"
        target_path = os.path.join(SCRIPT_DIR, filename)
        
        if os.path.exists(target_path):
            print(f"  Already downloaded: {filename}")
            continue
            
        # Find attachment in message parts
        parts = msg_details.get('payload', {}).get('parts', [])
        attachment_id = None
        for part in parts:
            if part.get('filename', '').endswith('.pdf'):
                attachment_id = part.get('body', {}).get('attachmentId')
                break
                
        if not attachment_id and 'parts' in msg_details.get('payload', {}):
            # Try deeper search
            for part in msg_details['payload']['parts']:
                if 'parts' in part:
                    for subpart in part['parts']:
                        if subpart.get('filename', '').endswith('.pdf'):
                            attachment_id = subpart.get('body', {}).get('attachmentId')
                            break
                            
        if attachment_id:
            print(f"  Downloading {filename}...")
            attachment = service.users().messages().attachments().get(
                userId='me', messageId=msg_id, id=attachment_id
            ).execute()
            data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
            with open(target_path, 'wb') as f:
                f.write(data)
            print(f"  Saved to {target_path}")
        else:
            print(f"  No PDF attachment found in message: {subject}")

if __name__ == "__main__":
    download_statements()
