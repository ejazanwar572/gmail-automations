import re

# Mock email content for testing
HDFC_UPI_MOCK = """
Dear Customer,

Greetings from HDFC Bank!

Rs.58.00 is debited from your account ending 9310 towards VPA Q838293821@ybl (RFA Hypermarket  Yelehanka new town) on 09-06-26.

UPI transaction reference no.: 415248514654.

If you did not authorize this transaction, please report it immediately.
"""

AMAZON_PAY_MOCK = """
Hi MD EJAZ ANWAR,

Your payment to SWIGGY BUSINESS is Approved.

Amount:    ₹255.0
Payment date:    Tuesday, 09 June, 2026 18:12:55 PM IST

Terms and Conditions: https://www.amazon.in

Thank you,
Amazon Pay
"""

def parse_hdfc_upi(text):
    print("--- Parsing HDFC UPI ---")
    # Patterns
    amount_pat = r"Rs\.?\s*([\d,]+\.\d{2})"
    account_pat = r"account ending (\d+)"
    vpa_pat = r"towards VPA\s+([a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+)"
    merchant_pat = r"towards VPA\s+[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\s*\(([^)]+)\)"
    date_pat = r"on\s+(\d{2}-\d{2}-\d{2})"
    ref_pat = r"(?:UPI transaction reference no\.|Ref no\.|Ref\.?)\s*:?\s*(\d+)"
    
    amount = re.search(amount_pat, text)
    account = re.search(account_pat, text)
    vpa = re.search(vpa_pat, text)
    merchant = re.search(merchant_pat, text)
    date = re.search(date_pat, text)
    ref = re.search(ref_pat, text)
    
    res = {
        "source": "HDFC UPI",
        "amount": float(amount.group(1).replace(",", "")) if amount else None,
        "account_last_4": account.group(1) if account else None,
        "vpa": vpa.group(1) if vpa else None,
        "merchant": merchant.group(1).strip() if merchant else None,
        "date": date.group(1) if date else None,
        "ref_no": ref.group(1) if ref else None
    }
    
    # Fallback: if VPA is parsed but no parenthesized merchant, try to use VPA description
    if res["vpa"] and not res["merchant"]:
        res["merchant"] = res["vpa"]
        
    return res

def parse_amazon_pay(text):
    print("--- Parsing Amazon Pay ---")
    payee_pat = r"Your payment to\s+(.*?)\s+is Approved"
    amount_pat = r"Amount:\s*₹?\s*([\d,]+\.?\d*)"
    date_pat = r"Payment date:\s*(.*?)$"
    
    payee = re.search(payee_pat, text)
    amount = re.search(amount_pat, text)
    date = re.search(date_pat, text, re.MULTILINE)
    
    res = {
        "source": "Amazon Pay",
        "amount": float(amount.group(1).replace(",", "")) if amount else None,
        "merchant": payee.group(1).strip() if payee else None,
        "date_str": date.group(1).strip() if date else None
    }
    return res

if __name__ == "__main__":
    hdfc_res = parse_hdfc_upi(HDFC_UPI_MOCK)
    print("HDFC Result:", hdfc_res)
    assert hdfc_res["amount"] == 58.00
    assert hdfc_res["account_last_4"] == "9310"
    assert hdfc_res["vpa"] == "Q838293821@ybl"
    assert hdfc_res["merchant"] == "RFA Hypermarket  Yelehanka new town"
    assert hdfc_res["date"] == "09-06-26"
    assert hdfc_res["ref_no"] == "415248514654"
    
    ap_res = parse_amazon_pay(AMAZON_PAY_MOCK)
    print("Amazon Pay Result:", ap_res)
    assert ap_res["amount"] == 255.0
    assert ap_res["merchant"] == "SWIGGY BUSINESS"
    
    print("\nAll assertion checks passed successfully!")
