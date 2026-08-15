#!/usr/bin/env python3
"""
Parse SBI Cashback statement PDFs into statements_data.json.
"""

import json
import os

import update_report


OUTPUT_FILE = os.path.join(update_report.PDF_DIR, "statements_data.json")


def main():
    data = update_report.build_sbi_statement_data()
    summary = []
    for statement in data["statements"]:
        debit_total = round(
            sum(float(t["amount"]) for t in statement["transactions"] if t.get("type") == "D"),
            2,
        )
        credit_total = round(
            sum(float(t["amount"]) for t in statement["transactions"] if t.get("type") == "C"),
            2,
        )
        summary.append({
            "month": statement["month"],
            "filename": statement["filename"],
            "debits": debit_total,
            "credits": credit_total,
            "txn_count": statement["transaction_count"],
        })

    data["summary"] = summary
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Parsed {len(data['statements'])} SBI statements -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
