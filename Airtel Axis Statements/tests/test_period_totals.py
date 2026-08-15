from datetime import date, datetime

from period_totals import calculate_lifetime_cashback, calculate_lifetime_spend, cycle_cashback


def test_lifetime_spend_deduplicates_and_excludes_accounting_entries():
    statements = {"statements": [{
        "month": "May 2026",
        "transactions": [
            {"date": "13/04/2026", "description": "SHOP ONE", "amount": 1000, "type": "Dr"},
            {"date": "13/04/2026", "description": "SHOP ONE", "amount": 1000, "type": "Dr"},
            {"date": "14/04/2026", "description": "GST", "amount": 180, "type": "Dr"},
            {"date": "15/04/2026", "description": "EMI PRINCIPAL - 1/12", "amount": 500, "type": "Dr"},
        ],
    }]}
    validation = [{"month": "May 2026", "validated": True}]
    alerts = [
        {"date": "13/05/2026", "amount": 200, "subject": "INR 200 spent at SHOP TWO", "message_id": "m1"},
        {"date": "13/05/2026", "amount": 200, "subject": "INR 200 spent at SHOP TWO", "message_id": "m1"},
        {"date": "14/05/2026", "amount": 300, "subject": "INR 300 spent at SHOP THREE"},
    ]
    result = calculate_lifetime_spend(statements, validation, alerts, date(2025, 3, 1))
    assert result["lifetime"] == 1500
    assert result["tracked_through"] == date(2026, 5, 14)


def test_pending_cashback_caps_each_category_per_cycle_and_ignores_unclassified():
    classifications = [
        {"date": "13/05/2026", "amount": 2000, "category": "airtel", "confidence": 1, "evidence_source": "receipt"},
        {"date": "14/05/2026", "amount": 3000, "category": "utilities", "confidence": 1, "evidence_source": "bill"},
    ]
    rows = [
        (datetime(2026, 5, 13), 2000, "AIRTEL", "AIRTEL"),
        (datetime(2026, 5, 14), 3000, "AIRTEL PAYMENTS", "AIRTEL"),
        (datetime(2026, 5, 15), 6000, "SWIGGY", "SWIGGY"),
        (datetime(2026, 5, 16), 9999, "AIRTEL UNKNOWN", "AIRTEL"),
    ]
    assert cycle_cashback(rows, classifications) == 1000


def test_lifetime_cashback_reconciles_confirmed_and_pending():
    statements = {"statements": [
        {"month": "April 2026", "cashback_earned": 281, "transactions": [{"date": "09/04/2026", "description": "CASHBACK CREDIT MAR26-NONTELECOM:100", "amount": 100, "type": "Cr"}]},
        {"month": "May 2026", "cashback_earned": 490, "transactions": [{"date": "09/05/2026", "description": "CASHBACK CREDIT APR26-NONTELECOM:250", "amount": 281, "type": "Cr"}]},
    ]}
    validation = [
        {"month": "April 2026", "validated": True, "cashback_verified": True, "cb_credited": 179},
        {"month": "May 2026", "validated": True, "cashback_verified": True, "cb_credited": 281},
    ]
    result = calculate_lifetime_cashback(statements, validation, [], [], date(2026, 5, 12))
    assert result == {"confirmed": 460, "pending": 490, "lifetime": 950, "confirmed_through": date(2026, 4, 12)}
