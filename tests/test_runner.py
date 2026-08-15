import os
import sqlite3
import unittest
import tracker_config

# Override paths for test isolation before any imports run
tracker_config.DB_PATH = "/Users/ejazanwar/.gemini/antigravity/test_expenses.db"
tracker_config.LEDGER_PATH = "/Users/ejazanwar/test_expense_ledger.md"

from local_expense_tracker import init_db, parse_hdfc_upi, parse_amazon_pay, log_transaction, generate_ledger_markdown
from tracker_config import DB_PATH, LEDGER_PATH

class TestExpenseLedger(unittest.TestCase):
    
    def setUp(self):
        # Clean up database and ledger from previous runs
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists(LEDGER_PATH):
            os.remove(LEDGER_PATH)
        init_db()

    def tearDown(self):
        # Clean up temporary test files
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists(LEDGER_PATH):
            os.remove(LEDGER_PATH)

    def test_database_initialization(self):
        """Verifies that the expenses table is initialized correctly."""
        self.assertTrue(os.path.exists(DB_PATH))
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(expenses)")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()
        
        expected_cols = ["id", "timestamp", "transaction_date", "source", "amount", "merchant", "account_ref", "transaction_ref", "vpa", "message_id"]
        for col in expected_cols:
            self.assertIn(col, columns)

    def test_hdfc_regex_parsing(self):
        """Verifies parsing of HDFC UPI emails."""
        body = "Rs.150.50 is debited from your account ending 1111 towards VPA test@okaxis (Google Pay) on 10-06-26. UPI transaction reference no.: 999999999999."
        txn = parse_hdfc_upi(body, "msg_hdfc_test", "2026-06-10")
        self.assertIsNotNone(txn)
        self.assertEqual(txn["amount"], 150.50)
        self.assertEqual(txn["account_ref"], "1111")
        self.assertEqual(txn["vpa"], "test@okaxis")
        self.assertEqual(txn["merchant"], "Google Pay")
        self.assertEqual(txn["transaction_date"], "2026-06-10")
        self.assertEqual(txn["transaction_ref"], "999999999999")

    def test_amazon_regex_parsing(self):
        """Verifies parsing of Amazon Pay emails."""
        body = "Hi Ejaz, Your payment to UBER TRIP is Approved. Amount: ₹320.00. Payment date: Tuesday, 09 June, 2026 18:00:00 PM IST"
        txn = parse_amazon_pay(body, "msg_ap_test", "2026-06-09")
        self.assertIsNotNone(txn)
        self.assertEqual(txn["amount"], 320.00)
        self.assertEqual(txn["merchant"], "UBER TRIP")
        self.assertEqual(txn["transaction_date"], "2026-06-09")

    def test_duplicate_prevention(self):
        """Verifies that SQLite constraints correctly prevent logging duplicate transactions."""
        txn = {
            "transaction_date": "2026-06-10",
            "source": "HDFC UPI",
            "amount": 100.00,
            "merchant": "Test Merchant",
            "account_ref": "1234",
            "transaction_ref": "REF123",
            "vpa": "test@upi",
            "message_id": "MSG123"
        }
        
        # Log first time -> Success
        success1 = log_transaction(txn)
        self.assertTrue(success1)
        
        # Log second time (duplicate txn ref) -> Failure
        success2 = log_transaction(txn)
        self.assertFalse(success2)
        
        # Log third time with different txn ref but same msg id -> Failure
        txn2 = txn.copy()
        txn2["transaction_ref"] = "REF456"
        success3 = log_transaction(txn2)
        self.assertFalse(success3)
        
        # Log fourth time with different ref and msg id -> Success
        txn3 = txn.copy()
        txn3["transaction_ref"] = "REF456"
        txn3["message_id"] = "MSG456"
        success4 = log_transaction(txn3)
        self.assertTrue(success4)

    def test_ledger_markdown_generation(self):
        """Verifies that the markdown ledger summarizes stats and lists entries correctly."""
        txn1 = {
            "transaction_date": "2026-06-10",
            "source": "HDFC UPI",
            "amount": 250.00,
            "merchant": "Swiggy",
            "account_ref": "1234",
            "transaction_ref": "REF1",
            "vpa": "swiggy@upi",
            "message_id": "MSG1"
        }
        txn2 = {
            "transaction_date": "2026-06-09",
            "source": "Amazon Pay",
            "amount": 750.00,
            "merchant": "Netflix",
            "account_ref": "",
            "transaction_ref": "REF2",
            "vpa": "",
            "message_id": "MSG2"
        }
        
        log_transaction(txn1)
        log_transaction(txn2)
        generate_ledger_markdown()
        
        self.assertTrue(os.path.exists(LEDGER_PATH))
        with open(LEDGER_PATH, "r") as f:
            content = f.read()
            
        self.assertIn("Total Spent**: ₹1,000.00", content)
        self.assertIn("Total Transactions**: 2", content)
        self.assertIn("Average Ticket Size**: ₹500.00", content)
        self.assertIn("Swiggy", content)
        self.assertIn("Netflix", content)

    def test_categorization(self):
        """Verifies that transaction logging automatically categorizes transactions."""
        txn = {
            "transaction_date": "2026-06-10",
            "source": "Amazon Pay",
            "amount": 255.00,
            "merchant": "Swiggy Business",
            "account_ref": "",
            "transaction_ref": "REF_CAT_TEST",
            "vpa": "",
            "message_id": "MSG_CAT_TEST"
        }
        
        log_transaction(txn)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT category FROM expenses WHERE transaction_ref = 'REF_CAT_TEST'")
        cat = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(cat, "Food & Dining")

if __name__ == "__main__":
    unittest.main()
