import unittest

import sync_alerts


class PhonePeReceiptClassificationTests(unittest.TestCase):
    def test_phonepe_mobile_recharge_receipt_moves_matching_upi_alert_to_phonepe_bucket(self):
        alerts = [{
            "date": "2026-07-14",
            "amount": 157.19,
            "merchant": "BSNLRecharge",
            "category": "pending",
            "message_id": "sbi-1",
        }]
        receipts = [{
            "date": "2026-07-14",
            "amount": 157.19,
            "description": "Payment for BSNL Mobile",
            "message_id": "phonepe-1",
        }]

        sync_alerts.apply_phonepe_receipts(alerts, receipts)

        self.assertEqual(alerts[0]["category"], "phonepe")
        self.assertEqual(alerts[0]["classification_evidence"], "phonepe-receipt")
        self.assertEqual(alerts[0]["phonepe_receipt_message_id"], "phonepe-1")

    def test_unmatched_upi_alert_uses_approved_phonepe_scan_and_pay_assumption(self):
        alerts = [{
            "date": "2026-07-16",
            "amount": 65.00,
            "merchant": "NiyasNallakandy",
            "category": "pending",
            "message_id": "sbi-2",
        }]

        sync_alerts.apply_phonepe_receipts(alerts, [])

        self.assertEqual(alerts[0]["category"], "other")
        self.assertEqual(alerts[0]["classification_evidence"], "user-approved-phonepe-upi-assumption")


if __name__ == "__main__":
    unittest.main()
