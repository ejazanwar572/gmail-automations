import os
import re
import sqlite3
import datetime
from tracker_config import DB_PATH, LEDGER_PATH, SCOPES, CREDENTIALS_FILE, TOKEN_FILE, GMAIL_QUERIES

# Try to import Google API clients; if missing, we will output guidance
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

# Mock data for demonstration and testing when offline
MOCK_EMAILS = [
    {
        "id": "mock_hdfc_1",
        "source": "HDFC UPI",
        "date": "2026-06-09",
        "body": "Dear Customer, Greetings from HDFC Bank! Rs.58.00 is debited from your account ending 9310 towards VPA Q838293821@ybl (RFA Hypermarket Yelehanka) on 09-06-26. UPI transaction reference no.: 415248514654."
    },
    {
        "id": "mock_hdfc_2",
        "source": "HDFC UPI",
        "date": "2026-06-08",
        "body": "Dear Customer, Greetings from HDFC Bank! Rs.1,200.00 is debited from your account ending 9310 towards VPA swiggy@upi (Swiggy Food) on 08-06-26. UPI transaction reference no.: 415248514699."
    },
    {
        "id": "mock_amazon_1",
        "source": "Amazon Pay",
        "date": "2026-06-09",
        "body": "Hi MD EJAZ ANWAR, Your payment to SWIGGY BUSINESS is Approved. Amount: ₹255.0. Payment date: Tuesday, 09 June, 2026 18:12:55 PM IST"
    },
    {
        "id": "mock_amazon_2",
        "source": "Amazon Pay",
        "date": "2026-06-05",
        "body": "Hi MD EJAZ ANWAR, Your payment to NETFLIX INDIA is Approved. Amount: ₹649.0. Payment date: Friday, 05 June, 2026 10:00:00 AM IST"
    }
]

def init_db():
    """Initializes the SQLite database, handles schema migrations, and configures default rules."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            transaction_date TEXT,
            source TEXT,
            amount REAL,
            merchant TEXT,
            account_ref TEXT,
            transaction_ref TEXT UNIQUE,
            vpa TEXT,
            message_id TEXT UNIQUE,
            category TEXT DEFAULT 'Uncategorized'
        )
    """)
    
    # Schema migration: Add category column if missing in older database versions
    try:
        cursor.execute("ALTER TABLE expenses ADD COLUMN category TEXT DEFAULT 'Uncategorized'")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
        
    # 2. Create category rules table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS category_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT UNIQUE,
            category TEXT
        )
    """)
    
    # Load default rules
    default_rules = [
        ('swiggy', 'Food & Dining'),
        ('zomato', 'Food & Dining'),
        ('netflix', 'Entertainment & Subs'),
        ('spotify', 'Entertainment & Subs'),
        ('zepto', 'Groceries'),
        ('hypermarket', 'Groceries'),
        ('farm fresh', 'Groceries'),
        ('cred', 'Card Payment'),
        ('amazon', 'Shopping'),
        ('firstclub', 'Entertainment & Subs'),
        ('uber', 'Travel'),
        ('ola', 'Travel')
    ]
    cursor.executemany("INSERT OR IGNORE INTO category_rules (pattern, category) VALUES (?, ?)", default_rules)
    
    conn.commit()
    conn.close()

def get_category_for_transaction(merchant, vpa):
    """Checks rules in database to categorize a transaction based on merchant or VPA."""
    category = "Uncategorized"
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT pattern, category FROM category_rules")
        rules = cursor.fetchall()
        conn.close()
        
        m_lower = merchant.lower() if merchant else ""
        v_lower = vpa.lower() if vpa else ""
        
        for pattern, cat in rules:
            pat_lower = pattern.lower()
            if pat_lower in m_lower or pat_lower in v_lower:
                category = cat
                break
    except Exception as e:
        print(f"Error looking up category: {e}")
    return category


def parse_hdfc_upi(body, msg_id, date_received):
    """Parses HDFC UPI transaction alert text using regex."""
    amount_pat = r"Rs\.?\s*([\d,]+\.\d{2})"
    account_pat = r"account ending (\d+)"
    vpa_pat = r"towards VPA\s+([a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+)"
    merchant_pat = r"towards VPA\s+[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\s*\(([^)]+)\)"
    date_pat = r"on\s+(\d{2}-\d{2}-\d{2})"
    ref_pat = r"(?:UPI transaction reference no\.|Ref no\.|Ref\.?)\s*:?\s*(\d+)"
    
    amount_m = re.search(amount_pat, body)
    account_m = re.search(account_pat, body)
    vpa_m = re.search(vpa_pat, body)
    merchant_m = re.search(merchant_pat, body)
    date_m = re.search(date_pat, body)
    ref_m = re.search(ref_pat, body)
    
    if not amount_m:
        return None
        
    amount = float(amount_m.group(1).replace(",", ""))
    account = account_m.group(1) if account_m else ""
    vpa = vpa_m.group(1) if vpa_m else ""
    merchant = merchant_m.group(1).strip() if merchant_m else vpa
    
    # Format date to YYYY-MM-DD
    txn_date = date_received
    if date_m:
        try:
            parts = date_m.group(1).split('-')
            # 09-06-26 -> 2026-06-09
            txn_date = f"20{parts[2]}-{parts[1]}-{parts[0]}"
        except Exception:
            pass
            
    ref_no = ref_m.group(1) if ref_m else f"N/A_{msg_id}"
    
    return {
        "transaction_date": txn_date,
        "source": "HDFC UPI",
        "amount": amount,
        "merchant": merchant,
        "account_ref": account,
        "transaction_ref": ref_no,
        "vpa": vpa,
        "message_id": msg_id
    }

def parse_amazon_pay(body, msg_id, date_received):
    """Parses Amazon Pay success email body using regex."""
    payee_pat = r"Your payment to\s+(.*?)\s+is Approved"
    amount_pat = r"Amount:\s*₹?\s*([\d,]+\.?\d*)"
    
    payee_m = re.search(payee_pat, body)
    amount_m = re.search(amount_pat, body)
    
    if not amount_m or not payee_m:
        return None
        
    amount = float(amount_m.group(1).replace(",", ""))
    merchant = payee_m.group(1).strip()
    
    return {
        "transaction_date": date_received,
        "source": "Amazon Pay",
        "amount": amount,
        "merchant": merchant,
        "account_ref": "",
        "transaction_ref": f"AP_{msg_id}",
        "vpa": "",
        "message_id": msg_id
    }

def log_transaction(txn):
    """Inserts a transaction dictionary into the SQLite database, ignoring duplicates."""
    if not txn:
        return False
    
    # Run auto-categorization
    category = get_category_for_transaction(txn.get("merchant", ""), txn.get("vpa", ""))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO expenses (transaction_date, source, amount, merchant, account_ref, transaction_ref, vpa, message_id, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            txn["transaction_date"],
            txn["source"],
            txn["amount"],
            txn["merchant"],
            txn["account_ref"],
            txn["transaction_ref"],
            txn["vpa"],
            txn["message_id"],
            category
        ))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Duplicate transaction_ref or message_id
        conn.close()
        return False

def generate_ledger_markdown():
    """Generates a beautiful Markdown ledger file summarizing expenses in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all transactions
    cursor.execute("SELECT transaction_date, source, amount, merchant, transaction_ref, category FROM expenses ORDER BY transaction_date DESC")
    rows = cursor.fetchall()
    
    # Calculate stats
    cursor.execute("SELECT COUNT(*), SUM(amount), AVG(amount) FROM expenses")
    total_txns, total_spent, avg_spent = cursor.fetchone()
    total_spent = total_spent or 0
    avg_spent = avg_spent or 0
    
    # Get top merchant
    cursor.execute("SELECT merchant, SUM(amount) FROM expenses GROUP BY merchant ORDER BY SUM(amount) DESC LIMIT 1")
    top_merchant_row = cursor.fetchone()
    top_merchant = f"{top_merchant_row[0]} (₹{top_merchant_row[1]:.2f})" if top_merchant_row else "N/A"
    
    conn.close()
    
    # Build markdown
    md = []
    md.append("# Expense Ledger")
    md.append(f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    md.append("\n## Financial Summary")
    md.append(f"- **Total Spent**: ₹{total_spent:,.2f}")
    md.append(f"- **Total Transactions**: {total_txns}")
    md.append(f"- **Average Ticket Size**: ₹{avg_spent:.2f}")
    md.append(f"- **Top Spending Merchant**: {top_merchant}")
    md.append("\n## Transaction Ledger")
    md.append("| Date | Source | Amount (INR) | Merchant / Payee | Category | Transaction Ref ID |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for row in rows:
        date, source, amount, merchant, ref, category = row
        md.append(f"| {date} | {source} | ₹{amount:,.2f} | {merchant} | {category} | `{ref}` |")
        
    with open(LEDGER_PATH, "w") as f:
        f.write("\n".join(md))
    
    print(f"Ledger successfully generated/updated at: {LEDGER_PATH}")

def get_gmail_service():
    """Authenticates and returns a Gmail API service instance."""
    if not GOOGLE_LIBS_AVAILABLE:
        print("Google API libraries are not installed. Run 'pip install google-auth-oauthlib google-api-python-client'")
        return None
        
    # Attempt to load auto-auth credentials from the local Gmail MCP config folder
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
            return build('gmail', 'v1', credentials=creds)
        except Exception as e:
            print(f"[!] Warning: Failed to load active Gmail MCP credentials: {e}")
            
    # Fallback to local project credentials if MCP credentials are not present
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"Error: {CREDENTIALS_FILE} not found. Please create an OAuth2 client credential in Google Cloud and save it here.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build('gmail', 'v1', credentials=creds)

def fetch_and_parse_gmail():
    """Connects to Gmail, fetches transaction alert emails, parses and logs them."""
    service = get_gmail_service()
    if not service:
        print("\n[!] Gmail API authentication failed or credentials.json is missing.")
        print("[!] Falling back to OFFLINE DEMO MODE using mock emails...")
        run_offline_demo()
        return

    print("Successfully connected to Gmail. Scanning for transactions...")
    logged_count = 0
    
    for query in GMAIL_QUERIES:
        try:
            results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
            messages = results.get('messages', [])
            
            for msg_summary in messages:
                msg_id = msg_summary['id']
                
                # Fetch full message content
                msg = service.users().messages().get(userId='me', id=msg_id).execute()
                payload = msg.get('payload', {})
                headers = payload.get('headers', [])
                
                # Extract internal date
                internal_date_ms = int(msg.get('internalDate', 0))
                date_received = datetime.datetime.fromtimestamp(internal_date_ms / 1000.0).strftime('%Y-%m-%d')
                
                # Extract subject and sender for routing
                subject = ""
                sender = ""
                for header in headers:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                    elif header['name'].lower() == 'from':
                        sender = header['value']
                
                # Retrieve body text
                body = ""
                parts = payload.get('parts', [])
                if parts:
                    for part in parts:
                        if part.get('mimeType') == 'text/plain':
                            import base64
                            body_data = part.get('body', {}).get('data', '')
                            body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                            break
                else:
                    import base64
                    body_data = payload.get('body', {}).get('data', '')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                
                # Route parsing based on sender/subject
                txn = None
                if "alerts@hdfcbank.bank.in" in sender or "UPI txn" in subject:
                    txn = parse_hdfc_upi(body, msg_id, date_received)
                elif "no-reply@amazonpay.in" in sender:
                    txn = parse_amazon_pay(body, msg_id, date_received)
                
                if txn:
                    success = log_transaction(txn)
                    if success:
                        print(f"Logged transaction: ₹{txn['amount']} to {txn['merchant']} ({txn['source']})")
                        logged_count += 1
                        
        except Exception as e:
            print(f"Error executing search query [{query}]: {e}")
            
    print(f"Scan finished. Logged {logged_count} new transactions.")
    generate_ledger_markdown()

def run_offline_demo():
    """Runs a complete test parsing flow using local mock emails to demonstrate ledger creation."""
    global DB_PATH, LEDGER_PATH
    # Override paths to avoid polluting production DB/ledger
    DB_PATH = os.path.join(os.path.dirname(DB_PATH), "demo_expenses.db")
    LEDGER_PATH = os.path.join(os.path.dirname(LEDGER_PATH), "demo_expense_ledger.md")
    
    # Initialize the demo DB
    init_db()
    
    print("--- Running Offline Expense Tracker Demo ---")
    logged_count = 0
    for email in MOCK_EMAILS:
        txn = None
        if email["source"] == "HDFC UPI":
            txn = parse_hdfc_upi(email["body"], email["id"], email["date"])
        elif email["source"] == "Amazon Pay":
            txn = parse_amazon_pay(email["body"], email["id"], email["date"])
            
        if txn:
            success = log_transaction(txn)
            if success:
                print(f"[NEW LOG] Verified: ₹{txn['amount']} to {txn['merchant']} ({txn['source']})")
                logged_count += 1
            else:
                print(f"[DUP SKIP] Skip duplicate transaction ID: {txn['transaction_ref']}")
                
    print(f"Offline parsing pass finished. Processed {len(MOCK_EMAILS)} mock emails, logged {logged_count} new entries.")
    generate_ledger_markdown()

if __name__ == "__main__":
    init_db()
    fetch_and_parse_gmail()
