import os
import re
import json
import sqlite3
import datetime
import urllib.request
from tracker_config import DB_PATH, LEDGER_PATH, SCOPES, CREDENTIALS_FILE, TOKEN_FILE, GMAIL_QUERIES

# Mock emails for AI parsing demonstration
MOCK_EMAILS = [
    {
        "id": "mock_ai_1",
        "source": "HDFC UPI",
        "date": "2026-06-09",
        "body": "Dear Customer, Greetings from HDFC Bank! Rs.58.00 is debited from your account ending 9310 towards VPA Q838293821@ybl (RFA Hypermarket Yelehanka) on 09-06-26. UPI transaction reference no.: 415248514654."
    },
    {
        "id": "mock_ai_2",
        "source": "Amazon Pay",
        "date": "2026-06-09",
        "body": "Hi MD EJAZ ANWAR, Your payment to SWIGGY BUSINESS is Approved. Amount: ₹255.0. Payment date: Tuesday, 09 June, 2026 18:12:55 PM IST"
    },
    {
        "id": "mock_ai_3",
        "source": "Netflix",
        "date": "2026-06-05",
        "body": "Hi MD EJAZ ANWAR, Your subscription payment of ₹649.00 to NETFLIX INDIA was successful on 05-06-2026. Txn ID: NETFLIX938472."
    }
]

# Import common database functions from local_expense_tracker to avoid duplication
from local_expense_tracker import init_db, get_category_for_transaction, log_transaction, generate_ledger_markdown

def parse_with_gemini_rest(email_body, api_key):
    """Calls Gemini REST API to extract transaction details into structured JSON."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    Analyze the following transaction email text and extract key details into a valid JSON object.
    Return ONLY a valid JSON object, with no markdown wrappers (no ```json).

    Email Text:
    \"\"\"{email_body}\"\"\"

    JSON Schema:
    {{
      "amount": float (the transaction amount as a number, e.g., 255.0),
      "currency": string (e.g., "INR"),
      "merchant": string (the name of the store or service, e.g., "Swiggy Business"),
      "transaction_date": string (format YYYY-MM-DD),
      "transaction_ref": string (unique reference ID or transaction ID),
      "category": string (one of: "Food & Dining", "Groceries", "Shopping", "Entertainment", "Utilities", "Travel", "Subscription", "Miscellaneous"),
      "account_ref": string (last 4 digits of account if mentioned, else empty string),
      "vpa": string (VPA address if mentioned, else empty string)
    }}
    """
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    req_body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=req_body,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode('utf-8')
            res_json = json.loads(res_data)
            
            # Extract content from response structure
            candidates = res_json.get('candidates', [])
            if candidates:
                content_text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                parsed_txn = json.loads(content_text.strip())
                return parsed_txn
    except Exception as e:
        print(f"Gemini API request failed: {e}")
    return None

# ledger generation is imported from local_expense_tracker

def run_offline_demo():
    print("--- Running Offline AI Expense Tracker Demo ---")
    logged_count = 0
    for email in MOCK_EMAILS:
        # Generate simulated AI output based on email body
        txn = None
        if "HDFC UPI" in email["source"]:
            txn = {
                "transaction_date": "2026-06-09",
                "source": "HDFC UPI",
                "amount": 58.00,
                "merchant": "RFA Hypermarket Yelehanka",
                "account_ref": "9310",
                "transaction_ref": "415248514654",
                "vpa": "Q838293821@ybl",
                "message_id": email["id"]
            }
        elif "Amazon Pay" in email["source"]:
            txn = {
                "transaction_date": "2026-06-09",
                "source": "Amazon Pay",
                "amount": 255.00,
                "merchant": "SWIGGY BUSINESS",
                "account_ref": "",
                "transaction_ref": f"AP_{email['id']}",
                "vpa": "",
                "message_id": email["id"]
            }
        elif "Netflix" in email["source"]:
            txn = {
                "transaction_date": "2026-06-05",
                "source": "Netflix Billing",
                "amount": 649.00,
                "merchant": "NETFLIX INDIA",
                "account_ref": "",
                "transaction_ref": "NETFLIX938472",
                "vpa": "",
                "message_id": email["id"]
            }
            
        if txn:
            success = log_transaction(txn)
            if success:
                print(f"[NEW LOG - AI] Logged: ₹{txn['amount']} to {txn['merchant']} ({txn['source']})")
                logged_count += 1
            else:
                print(f"[DUP SKIP - AI] Skip duplicate: {txn['transaction_ref']}")
                
    print(f"Offline AI pass finished. Logged {logged_count} entries.")
    generate_ledger_markdown()

def main():
    init_db()
    # Check for Gemini API key
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("\n[!] GEMINI_API_KEY environment variable is not set.")
        print("[!] Running in OFFLINE DEMO MODE with simulated AI parsing...")
        run_offline_demo()
        return
        
    print("AI-Augmented Parser started using Gemini API...")
    # Real pipeline using Gmail + AI would run here
    # For demonstration, we will show how the parser handles a mock payload via the real API key
    print("Testing Gemini REST connection...")
    test_body = "Dear Customer, Rs.500.00 debited from account ending 1234 towards VPA netflix@upi on 2026-06-09. Ref: 1234567890."
    parsed = parse_with_gemini_rest(test_body, api_key)
    if parsed:
        print("Successfully connected and parsed email via Gemini API!")
        print("AI Extracted Result:", json.dumps(parsed, indent=2))
        parsed["message_id"] = "live_test_msg_1"
        parsed["source"] = "Gemini AI Parser"
        log_transaction(parsed)
        generate_ledger_markdown()
    else:
        print("Gemini API connection failed. Running offline demo...")
        run_offline_demo()

if __name__ == "__main__":
    main()
