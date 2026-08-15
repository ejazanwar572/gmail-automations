from datetime import datetime

from transaction_classifier import classify_transactions


def test_sms_evidence_assigns_airtel_payment_to_utilities_only():
    transactions = [
        (datetime(2026, 7, 18), 1857.70, "INR 1857.7 SPENT AT AIRTEL PAYM", "AIRTEL PAYM"),
    ]
    evidence = [
        {
            "date": "18/07/2026",
            "amount": 1857.70,
            "category": "utilities",
            "confidence": 1.0,
            "evidence_source": "Google Messages",
        }
    ]

    result = classify_transactions(transactions, evidence)

    assert result["utilities"] == [
        {
            "date": "Jul 18",
            "amount": 1857.70,
            "merchant": "AIRTEL PAYM",
            "evidence_source": "Google Messages",
        }
    ]
    assert result["airtel"] == []
    assert result["unclassified"] == []


def test_generic_airtel_payment_without_strong_evidence_stays_unclassified():
    transactions = [
        (datetime(2026, 7, 15), 919.22, "INR 919.22 SPENT AT AIRTEL PAYM", "AIRTEL PAYM"),
    ]

    result = classify_transactions(transactions, [])

    assert result["airtel"] == []
    assert result["utilities"] == []
    assert result["unclassified"][0]["amount"] == 919.22
