#!/usr/bin/env python3
"""
Parse decrypted HDFC Diners Club Black Metal statement PDFs into statements_data.json,
update statement_rewards.json baseline, and synchronize cycle evidence.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from datetime import datetime
from typing import Any, Dict, List

import pypdf


def get_env_password(var_name: str = "HDFC_DCBM_PASSWORD", default: str = "") -> str:
    """Load password from environment variable, falling back to root-level .env file."""
    val = os.environ.get(var_name)
    if val:
        return val.strip().strip('"').strip("'")
    current_dir = Path(__file__).resolve().parent
    for _ in range(4):
        env_path = current_dir / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == var_name:
                            return v.strip().strip('"').strip("'")
            except Exception:
                pass
        current_dir = current_dir.parent
    return default


def parse_all_statements(card_dir: Path | str) -> Dict[str, Any]:
    card_dir = Path(card_dir)
    password = get_env_password("HDFC_DCBM_PASSWORD", "")
    
    pdf_files = sorted(card_dir.glob("statement_*.pdf"))
    if not pdf_files:
        # Check for original HDFC statement names e.g. 0036*.pdf
        pdf_files = sorted(card_dir.glob("0036*.pdf"))
    
    statements: List[Dict[str, Any]] = []
    all_statement_txs: List[Dict[str, Any]] = []

    cum_base = 0
    cum_acc = 0
    cum_bonus = 0
    cum_earned = 0
    cum_redeemed = 0
    latest_closing_points = 0
    latest_stmt_date = None

    for pdf_file in pdf_files:
        try:
            reader = pypdf.PdfReader(str(pdf_file))
            if reader.is_encrypted:
                if not password:
                    continue
                # Try variations if exact fails
                for p in [password, password.lower(), password.upper(), password.strip()]:
                    if reader.decrypt(p) != 0:
                        break
                else:
                    continue
        except Exception as e:
            print(f"Warning: could not open/decrypt {pdf_file.name}: {e}")
            continue

        text = "\n".join([page.extract_text() or "" for page in reader.pages])

        # Extract statement date, due date, amounts
        stmt_date_m = re.search(r"As on\s*:\s*(\d{1,2}\s+[A-Za-z]{3},\s+\d{4})", text)
        due_date_m = re.search(r"DUE DATE\s*\n\s*(\d{1,2}\s+[A-Za-z]{3},\s+\d{4})", text)
        total_due_m = re.search(r"TOTAL AMOUNT DUE\s*\n\s*C?([\d,]+\.\d{2})", text)
        min_due_m = re.search(r"MINIMUM DUE\s*\n\s*C?([\d,]+\.\d{2})", text)

        stmt_date = datetime.strptime(stmt_date_m.group(1), "%d %b, %Y").date() if stmt_date_m else None
        due_date = datetime.strptime(due_date_m.group(1), "%d %b, %Y").date() if due_date_m else None
        total_due = float(total_due_m.group(1).replace(",", "")) if total_due_m else 0.0
        min_due = float(min_due_m.group(1).replace(",", "")) if min_due_m else 0.0

        # Reward points section
        rp_m = re.search(r"Opening Balance.*?(\d[\d,]*)\s+(\d[\d,]*)\s+(\d[\d,]*)\s+(\d[\d,]*)", text, re.DOTALL)
        opening_rp = int(rp_m.group(1).replace(",", "")) if rp_m else 0
        earned_rp = int(rp_m.group(2).replace(",", "")) if rp_m else 0
        disbursed_rp = int(rp_m.group(3).replace(",", "")) if rp_m else 0
        closing_rp = opening_rp + earned_rp - disbursed_rp

        # Bonus programs breakdown
        bonus_programs: Dict[str, int] = {}
        for bm in re.finditer(r"(?:^\s*\d+\s+)?([A-Za-z0-9_ ]+?)\s+(\d+)\s+pts", text, re.MULTILINE):
            prog_name = bm.group(1).strip()
            if prog_name.lower() == "total":
                continue
            pts = int(bm.group(2))
            bonus_programs[prog_name] = pts

        acc_in_statement = sum(pts for name, pts in bonus_programs.items() if "smartbuy" in name.lower())
        bonus_promo_in_statement = sum(pts for name, pts in bonus_programs.items() if "smartbuy" not in name.lower())
        base_in_statement = max(0, earned_rp - acc_in_statement - bonus_promo_in_statement)

        cum_earned += earned_rp
        cum_redeemed += disbursed_rp
        cum_base += base_in_statement
        cum_acc += acc_in_statement
        cum_bonus += bonus_promo_in_statement
        latest_closing_points = closing_rp
        if stmt_date:
            latest_stmt_date = stmt_date

        # Transaction items
        pattern = r"(\d{2}/\d{2}/\d{4})\|\s*(\d{2}:\d{2})\s*(.*?)\s+C\s*([\d,]+\.\d{2})\s*([l\+])?"
        txs: List[Dict[str, Any]] = []
        for m in re.finditer(pattern, text):
            raw_d, t_time, desc, amt_str, flag = m.groups()
            tx_d = datetime.strptime(raw_d, "%d/%m/%Y").date()
            amt = float(amt_str.replace(",", ""))
            flag = flag or ""
            is_cr = "+" in flag or "PAYMENT" in desc or "REFUND" in desc

            rp_match = re.search(r"\+\s*(\d+)", desc)
            rp_line = int(rp_match.group(1)) if rp_match else 0
            clean_desc = re.sub(r"\+\s*\d+", "", desc).strip()

            tx_item = {
                "date": tx_d.isoformat(),
                "time": t_time,
                "merchant": clean_desc,
                "amount": amt,
                "type": "credit" if is_cr else "debit",
                "reward_points": rp_line,
                "card_ending": "2360",
                "card_role": "Primary",
                "source": "statement-pdf",
                "statement_file": pdf_file.name,
            }
            txs.append(tx_item)
            all_statement_txs.append(tx_item)

        statements.append({
            "filename": pdf_file.name,
            "statement_date": stmt_date.isoformat() if stmt_date else None,
            "due_date": due_date.isoformat() if due_date else None,
            "total_amount_due": total_due,
            "minimum_due": min_due,
            "points": {
                "opening": opening_rp,
                "earned": earned_rp,
                "redeemed": disbursed_rp,
                "closing": closing_rp,
                "base_points": base_in_statement,
                "accelerated_points": acc_in_statement,
                "bonus_promo_points": bonus_promo_in_statement,
                "bonus_programs": bonus_programs,
            },
            "transaction_count": len(txs),
            "transactions": txs,
        })

    # Sort statements chronologically
    statements.sort(key=lambda s: s.get("statement_date") or "")

    # Include post-statement unbilled alerts from gmail_alerts.json for complete real-time view
    unbilled_txs: List[Dict[str, Any]] = []
    alerts_file = card_dir / "gmail_alerts.json"
    if alerts_file.exists():
        try:
            alerts = json.loads(alerts_file.read_text())
            cutoff = latest_stmt_date.isoformat() if latest_stmt_date else ""
            for a in alerts:
                if a.get("date", "") > cutoff:
                    unbilled_txs.append({
                        "date": a.get("date"),
                        "merchant": a.get("merchant"),
                        "amount": a.get("amount"),
                        "type": "debit",
                        "source": "gmail-api-unbilled",
                        "card_ending": a.get("card_ending", "2360"),
                        "card_role": a.get("card_role", "Primary"),
                    })
        except Exception:
            pass

    combined_transactions = all_statement_txs + unbilled_txs

    payload = {
        "generated_at": datetime.now().isoformat(),
        "notes": [
            "Official statement data parsed directly from decrypted HDFC statement PDFs.",
            "Transactions include settled statement line items + unbilled live Gmail alerts.",
        ],
        "statements_count": len(statements),
        "statements": statements,
        "transactions": combined_transactions,
    }

    # Write statements_data.json
    (card_dir / "statements_data.json").write_text(json.dumps(payload, indent=2))

    # Update statement_rewards.json if we have statement data
    if statements and latest_stmt_date:
        rewards_payload = {
            "source": f"HDFC cumulative statement history through {latest_stmt_date.strftime('%B %Y')}",
            "scope": "lifetime",
            "statement_start": statements[-1]["transactions"][0]["date"] if statements[-1]["transactions"] else "2026-08-14",
            "statement_end": latest_stmt_date.isoformat(),
            "total_points": cum_earned,
            "closing_points": latest_closing_points,
            "redeemed_points": cum_redeemed,
            "base_points": cum_base,
            "accelerated_points": cum_acc,
            "bonus_points": cum_bonus,
        }
        (card_dir / "statement_rewards.json").write_text(json.dumps(rewards_payload, indent=2))

        # Update cycle_evidence.json
        cycle_payload = {
            "card_ending": "2360",
            "cycle": {
                "end_day": 13,
                "start_day": 14,
            },
            "latest_statement": {
                "period_start": statements[-1].get("statement_date"),
                "period_end": latest_stmt_date.isoformat(),
                "statement_date": latest_stmt_date.isoformat(),
                "source_filename": statements[-1]["filename"],
            },
            "schema_version": 1,
            "status": "confirmed",
        }
        (card_dir / "cycle_evidence.json").write_text(json.dumps(cycle_payload, indent=2))

    return payload


if __name__ == "__main__":
    card_dir = Path(__file__).resolve().parent
    result = parse_all_statements(card_dir)
    print(json.dumps({
        "ok": True,
        "statements_parsed": result.get("statements_count", 0),
        "total_transactions": len(result.get("transactions", [])),
    }, indent=2))
