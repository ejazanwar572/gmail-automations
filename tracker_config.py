import os

# Database and Ledger Configurations
DB_PATH = "/Users/ejazanwar/.gemini/antigravity/expenses.db"
LEDGER_PATH = "/Users/ejazanwar/expense_ledger.md"
SETTINGS_PATH = "/Users/ejazanwar/.gemini/antigravity/settings.json"

# Google API Configurations
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')

# Search Queries
GMAIL_QUERIES = [
    'from:alerts@hdfcbank.bank.in subject:"UPI txn"',
    'from:no-reply@amazonpay.in subject:"successful" subject:"payment"'
]
