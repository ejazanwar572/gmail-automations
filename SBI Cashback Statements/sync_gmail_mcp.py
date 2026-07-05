#!/usr/bin/env python3
import os
import re
import json
import sys
from datetime import datetime

ALERTS_FILE = "/Users/ejazanwar/Documents/Gmail Automations/SBI Cashback Statements/gmail_alerts.json"
STEP_DIR = "/Users/ejazanwar/.gemini/antigravity/brain/a9fcd66a-382c-4edf-9ca7-a3fe14a6acaf/.system_generated/steps"
ROOT_DIR = os.path.dirname(os.path.dirname(ALERTS_FILE))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import card_freshness

def clean_html(html_text):
    text = re.sub(r'<[^>]+>', ' ', html_text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_date_str(d_str):
    # DD/MM/YY
    if '/' in d_str:
        d, m, y = d_str.split('/')
        return f"{d.zfill(2)}/{m.zfill(2)}/20{y}"
    # D Month YY, e.g. "6 Jun 26"
    for fmt in ("%d %b %y", "%d %B %y", "%d %b %Y", "%d %B %Y"):
        try:
            dt = datetime.strptime(d_str, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            pass
    return d_str

def main():
    # 1. Load existing alerts
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []
        
    previous_count = len(alerts)
    print(f"Loaded {len(alerts)} existing alerts.")

    # Convert to set of tuples for easy duplicate checking
    # Tuple format: (date, amount, merchant)
    existing_set = set()
    for a in alerts:
        merchant = "Unknown"
        m_match = re.search(r'at\s+(.*)', a.get("subject", ""), re.IGNORECASE)
        if m_match:
            merchant = m_match.group(1).strip()
        existing_set.add((a["date"], float(a["amount"]), merchant))

    new_count = 0
    skipped_duplicate_count = 0
    
    # 2. Scan step directories
    if os.path.exists(STEP_DIR):
        for folder in sorted(os.listdir(STEP_DIR), key=lambda x: int(x) if x.isdigit() else 999):
            folder_path = os.path.join(STEP_DIR, folder)
            if not os.path.isdir(folder_path):
                continue
            
            file_path = os.path.join(folder_path, "output.txt")
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
                
            cleaned = clean_html(content)
            
            # Format 1: Rs.X spent on your SBI Credit Card ending 0846 at MERCHANT on DATE
            m1 = re.search(
                r'Rs\.([\d,]+\.\d{2})\s+spent on your SBI Credit Card ending 0846 at (.*?)\s+on\s+(\d{2}/\d{2}/\d{2})',
                cleaned,
                re.IGNORECASE
            )
            # Format 2: Trxn. of Rs.1,999.00 done on your credit card ending 0846 ... at MERCHANT on DATE
            m2 = re.search(
                r'Trxn\.\s+of\s+Rs\.([\d,]+\.\d{2})\s+done\s+on\s+your\s+credit\s+card\s+ending\s+0846\s+.*?at\s+(.*?)\s+on\s+(\d{1,2}\s+[a-z]{3}\s+\d{2})',
                cleaned,
                re.IGNORECASE
            )
            
            if m1:
                amt = float(m1.group(1).replace(',', ''))
                merchant = m1.group(2).strip()
                date_formatted = parse_date_str(m1.group(3).strip())
            elif m2:
                amt = float(m2.group(1).replace(',', ''))
                merchant = m2.group(2).strip()
                date_formatted = parse_date_str(m2.group(3).strip())
            else:
                continue
                
            # Check for duplicate
            key = (date_formatted, amt, merchant)
            if key not in existing_set:
                subject_with_merchant = f"Transaction Alert from CASHBACK SBI Card at {merchant}"
                alerts.append({
                    "subject": subject_with_merchant,
                    "date": date_formatted,
                    "amount": amt
                })
                existing_set.add(key)
                new_count += 1
                print(f"Added new alert: {date_formatted} | ₹{amt} at {merchant}")
            else:
                skipped_duplicate_count += 1

    # 3. Sort alerts by date descending
    def get_alert_date(alert):
        try:
            return datetime.strptime(alert["date"], "%d/%m/%Y")
        except ValueError:
            return datetime.min

    alerts.sort(key=get_alert_date, reverse=True)

    # 4. Write back to alerts file
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)

    metadata = card_freshness.write_sync_metadata(
        os.path.dirname(ALERTS_FILE),
        card_name="SBI Cashback Credit Card",
        card_ending="0846",
        source="gmail-plugin-step-logs",
        query='from:onlinesbicard@sbicard.com subject:"Transaction Alert from CASHBACK SBI Card" "ending 0846"',
        alerts=alerts,
        previous_count=previous_count,
        new_count=new_count,
        skipped_duplicate_count=skipped_duplicate_count,
    )
        
    print(f"Finished. Total alerts in file: {len(alerts)} ({new_count} new alerts added, {skipped_duplicate_count} duplicates skipped).")
    print(f"Sync metadata saved → {os.path.join(os.path.dirname(ALERTS_FILE), 'sync_metadata.json')}")

if __name__ == "__main__":
    main()
