#!/usr/bin/env python3
"""
OAuth Reauthentication Helper for Gmail Credit Card Automations.
Runs the OAuth flow and saves the token to all credit card statement folders.
"""

import os
import json
import shutil
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

BASE_DIR = "/Users/ejazanwar/Documents/Gmail Automations"
KEYS_FILE = "/Users/ejazanwar/.gmail-mcp/gcp_oauth.keys.json"
CENTRAL_TOKEN = os.path.join(BASE_DIR, "token.json")

CARD_DIRS = [
    os.path.join(BASE_DIR, "Airtel Axis Statements"),
    os.path.join(BASE_DIR, "Flipkart Axis Statements"),
    os.path.join(BASE_DIR, "SBI Cashback Statements")
]

def main():
    if not os.path.exists(KEYS_FILE):
        # Fallback to the other filename if needed
        alt_keys = "/Users/ejazanwar/.gmail-mcp/gcp-oauth.keys.json"
        if os.path.exists(alt_keys):
            shutil.copy(alt_keys, KEYS_FILE)
            print(f"Copied {alt_keys} to {KEYS_FILE}")
        else:
            print(f"[ERROR] OAuth keys file not found at {KEYS_FILE}")
            return

    print("Starting Google OAuth Reauthentication flow...")
    print("This will open a browser window to authorize Gmail access.")
    
    flow = InstalledAppFlow.from_client_secrets_file(KEYS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    
    # Save the central token
    with open(CENTRAL_TOKEN, 'w') as f:
        f.write(creds.to_json())
    print(f"Saved central token to {CENTRAL_TOKEN}")
    
    # Copy to the respective directories
    for d in CARD_DIRS:
        if os.path.exists(d):
            dest_token = os.path.join(d, "token.json")
            shutil.copy(CENTRAL_TOKEN, dest_token)
            print(f"Copied token.json to {d}/")
            
            # Also overwrite their local credentials.json with the token json (just in case they read it)
            dest_creds = os.path.join(d, "credentials.json")
            shutil.copy(CENTRAL_TOKEN, dest_creds)
            print(f"Copied credentials.json to {d}/")

    print("\nReauthentication completed successfully!")

if __name__ == "__main__":
    main()
