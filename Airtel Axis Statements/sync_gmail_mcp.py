#!/usr/bin/env python3
import os
import re
import json
from datetime import datetime
from email.utils import parsedate_to_datetime

ALERTS_FILE = "/Users/ejazanwar/Documents/Gmail Automations/Airtel Axis Statements/gmail_alerts.json"
STEP_DIR = "/Users/ejazanwar/.gemini/antigravity/brain/bbed8903-cd94-4ab4-aa79-91383f9837a5/.system_generated/steps"

def clean_html(html_text):
    text = re.sub(r'<[^>]+>', ' ', html_text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def main():
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, 'r') as f:
            alerts = json.load(f)
    else:
        alerts = []

    print(f"Loaded {len(alerts)} existing alerts.")

    # Convert existing alerts to set for duplicate checking
    existing_set = set()
    for a in alerts:
        existing_set.add((a["date"], float(a["amount"]), a["subject"]))

    new_count = 0

    if os.path.exists(STEP_DIR):
        for folder in sorted(os.listdir(STEP_DIR), key=lambda x: int(x) if x.isdigit() else 999):
            folder_path = os.path.join(STEP_DIR, folder)
            if not os.path.isdir(folder_path):
                continue
            
            # We only want to parse steps that are Airtel Axis alerts (174, 178, 180, 182, 184, 186, 188, 190, 192, 194)
            if folder not in ["174", "178", "180", "182", "184", "186", "188", "190", "192", "194"]:
                continue
                
            file_path = os.path.join(folder_path, "output.txt")
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()

            # 1. Parse Subject
            subject_match = re.search(r'^Subject:\s*(.*)$', content, re.MULTILINE)
            subject = subject_match.group(1).strip() if subject_match else ""
            if not subject:
                continue

            # 2. Parse Date Header
            date_match = re.search(r'^Date:\s*(.*)$', content, re.MULTILINE)
            date_header = date_match.group(1).strip() if date_match else ""
            if not date_header:
                continue

            try:
                dt = parsedate_to_datetime(date_header)
                date_formatted = dt.strftime("%d/%m/%Y")
            except Exception as e:
                print(f"Error parsing date {date_header}: {e}")
                continue

            # 3. Parse Amount from Subject (optional decimals)
            amount_match = re.search(r'INR\s*([\d,]+(?:\.\d{2})?)', subject, re.IGNORECASE)
            if not amount_match:
                amount_match = re.search(r'([\d,]+(?:\.\d{2})?)', subject)

            if not amount_match:
                print(f"Could not parse amount from subject: {subject}")
                continue

            amount = float(amount_match.group(1).replace(',', ''))

            # 4. Parse Merchant Name from body using Merchant Name:\s*\n*\s*([^\n]+)
            # Find the HTML body block in output.txt
            body_start = content.find("<!DOCTYPE html")
            if body_start == -1:
                body_start = content.find("<html")
            
            if body_start != -1:
                body_content = content[body_start:]
            else:
                body_content = content

            merchant_name = "Unknown"
            # Apply exact regex: Merchant Name:\s*\n*\s*([^\n]+)
            m_match = re.search(r'Merchant\s+Name:\s*\n*\s*([^\n]+)', body_content, re.IGNORECASE)
            if m_match:
                # Strip HTML if any (e.g. if the matched line has tags)
                merchant_name = clean_html(m_match.group(1)).strip()
                # Some post-processing to clean up any remaining trash
                merchant_name = re.sub(r'\s+', ' ', merchant_name)
            
            # Format subject with merchant
            if merchant_name != "Unknown" and merchant_name not in subject:
                subject_with_merchant = f"{subject} at {merchant_name}"
            else:
                subject_with_merchant = subject

            # Check duplicate
            key = (date_formatted, amount, subject_with_merchant)
            if key not in existing_set:
                alerts.append({
                    "subject": subject_with_merchant,
                    "date": date_formatted,
                    "amount": amount
                })
                existing_set.add(key)
                new_count += 1
                print(f"Added new alert: {date_formatted} | ₹{amount} at {merchant_name}")

    # Sort alerts by date descending
    def get_alert_date(alert):
        try:
            return datetime.strptime(alert["date"], "%d/%m/%Y")
        except ValueError:
            return datetime.min

    alerts.sort(key=get_alert_date, reverse=True)

    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)

    print(f"Finished. Total alerts in file: {len(alerts)} ({new_count} new alerts added).")

if __name__ == "__main__":
    main()
