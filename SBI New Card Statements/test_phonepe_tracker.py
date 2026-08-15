import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import phonepe_tracker


class PhonePeTrackerTests(unittest.TestCase):
    def test_builds_four_reward_buckets_and_three_milestones(self):
        alerts = [
            {"date": "2026-07-02", "amount": 1000, "merchant": "PhonePe Recharge", "category": "phonepe"},
            {"date": "2026-07-03", "amount": 2000, "merchant": "PhonePe Insurance", "category": "insurance"},
            {"date": "2026-07-04", "amount": 3000, "merchant": "Amazon", "category": "online"},
            {"date": "2026-07-05", "amount": 4000, "merchant": "Store", "category": "other"},
        ]
        payload = phonepe_tracker.build_summary(alerts, {}, as_of=date(2026, 7, 16), run_id="run-1")
        self.assertEqual(payload["card"], {"name": "PhonePe SBI Card SELECT BLACK", "ending": "3366"})
        self.assertEqual([row["earned"] for row in payload["benefits"]], [100, 200, 150, 40])
        self.assertEqual([row["cap"] for row in payload["benefits"]], [1500, 500, 1000, 2000])
        self.assertEqual(payload["reward_points"]["estimated"], 490)
        self.assertEqual(payload["annual_fee"]["waiver_spend"], 300000)
        self.assertEqual(payload["annual_milestone"]["target"], 500000)

    def test_atomic_outputs_require_matching_live_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "gmail_alerts.json").write_text("[]")
            (root / "sync_metadata.json").write_text(json.dumps({"source": "gmail-api", "run_id": "r1", "alert_count": 0, "synced_at": "2026-07-16T04:30:00Z", "latest_alert_date": "2026-07-15"}))
            validation = phonepe_tracker.validate(root)
            self.assertTrue(validation["ok"])
            phonepe_tracker.write_outputs(root, as_of=date(2026, 7, 16))
            self.assertEqual(json.loads((root / "dashboard_summary.json").read_text())["run_id"], "r1")

    def test_reward_buckets_exclude_transactions_below_sbi_minimum(self):
        alerts = [
            {"date": "2026-07-05", "amount": 95, "merchant": "Small QR", "category": "other"},
            {"date": "2026-07-06", "amount": 100, "merchant": "Eligible QR", "category": "other"},
        ]

        payload = phonepe_tracker.build_summary(alerts, {}, as_of=date(2026, 7, 16), run_id="run-2")

        other = next(row for row in payload["benefits"] if row["name"] == "Other eligible spends")
        self.assertEqual(other["spend"], 100)
        self.assertEqual(other["earned"], 1)
        self.assertEqual(payload["cycle"]["spend"], 195)


if __name__ == "__main__":
    unittest.main()
