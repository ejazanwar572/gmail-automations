import importlib.util
import json
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))
import card_benefit_tracker as tracker


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workflow = load_module("hsbc_run_workflow", Path(__file__).resolve().parents[1] / "run_workflow.py")


class WorkflowTests(unittest.TestCase):
    def test_modes_run_exact_sequences_and_default_to_gmail_api(self):
        expected = {
            None: ["sync_alerts.py", "parse_statements.py", "validate_statements.py", "update_report.py"],
            "gmail-api": ["sync_alerts.py", "parse_statements.py", "validate_statements.py", "update_report.py"],
            "mcp-step-logs": ["sync_gmail_mcp.py", "parse_statements.py", "validate_statements.py", "update_report.py"],
            "none": ["parse_statements.py", "validate_statements.py", "update_report.py"],
        }
        for mode, scripts in expected.items():
            with self.subTest(mode=mode), mock.patch.object(workflow.subprocess, "run") as run:
                run.return_value.returncode = 0
                argv = ["run_workflow.py"] + ([] if mode is None else ["--sync-source", mode])
                with mock.patch.object(sys, "argv", argv):
                    self.assertEqual(0, workflow.main())
                self.assertEqual(scripts, [Path(call.args[0][1]).name for call in run.call_args_list])

    def test_failure_stops_later_steps(self):
        outcomes = [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 7)]
        with mock.patch.object(workflow.subprocess, "run", side_effect=outcomes) as run:
            with mock.patch.object(sys, "argv", ["run_workflow.py", "--sync-source", "none"]):
                self.assertEqual(7, workflow.main())
        self.assertEqual(2, run.call_count)


class HSBCBenefitTests(unittest.TestCase):
    def config(self):
        return {
            "card_name": "HSBC Live+ Credit Card", "card_ending": "8690", "variant_status": "confirmed",
            "cycle": {"start": "2026-06-29", "end": "2026-07-28"},
            "annual_fee": {"amount": 999, "waiver_spend": 200000, "period_start": "2026-06-29", "period_end": "2027-06-28"},
            "welcome": {
                "spend_target": 20000,
                "reward": 1000,
                "activation_proxy_date": "2026-06-29",
                "activation_proxy_source": "Supported by HSBC app setup and PIN reset.",
                "window_days": 30,
                "evidence_state": "provisional",
            },
            "benefit_rules": [
                {"name": "10% Dining, Food Delivery and Grocery", "rate": .10, "monthly_cap": 1200, "match": ["ZOMATO", "GROCERY"]},
                {"name": "1.5% Other Eligible Spends", "rate": .015, "monthly_cap": None, "match": ["DEFAULT"]},
            ],
        }

    def modern_config(self):
        config = self.config()
        config["cashback_policy"] = {
            "version": "2026-07-26",
            "effective_from": "2026-07-26",
            "reviewed_at": "2026-07-29",
            "accelerated_rate": 0.10,
            "accelerated_cap": 1200,
            "standard_rate": 0.015,
            "categories": {
                "Dining and food delivery": {"mccs": ["5812", "5814"], "keywords": ["ZOMATO", "SWIGGY"]},
                "Grocery": {"mccs": ["5411"], "keywords": ["GROCERY", "BLINKIT"]},
                "Shopping": {"mccs": ["5732"], "keywords": ["ELECTRONICS"]},
                "Utilities": {"mccs": ["4814", "4900"], "keywords": ["UTILITY"]},
            },
            "excluded_mccs": ["8062", "4111", "6540"],
            "merchant_overrides": {
                "standard": ["AMAZON", "FLIPKART"],
                "temporary_accelerated": [
                    {"merchant": "MYNTRA", "through": "2026-10-31", "category": "Shopping"},
                ],
            },
            "fuel_offer": {
                "effective_from": "2026-07-26", "ends_on": "2026-12-31",
                "eligible_mccs": ["5541", "5542", "5983"], "minimum_transaction": 1000,
                "maximum_transaction": 5000, "quarterly_target": 10000, "reward": 250,
                "source_conflict": True,
            },
            "lounge": {
                "domestic_annual": 2, "domestic_per_half_year": 1,
                "international_annual": 1, "international_available_from": "2026-09-01",
            },
        }
        return config

    def test_period_filters_and_fixed_cycle_roll_forward(self):
        alerts = [
            {"date": "2026-06-28", "amount": 9000, "merchant": "old"},
            {"date": "2026-06-29", "amount": 1000, "merchant": "start"},
            {"date": "2026-07-29", "amount": 2000, "merchant": "next"},
            {"date": "2027-06-29", "amount": 8000, "merchant": "late"},
        ]
        result = tracker.calculate_benefits(self.config(), alerts, as_of=date(2026, 8, 1))
        self.assertEqual(("2026-07-29", "2026-08-28"), (result["cycle_start"], result["cycle_end"]))
        self.assertEqual(3000, result["annual_fee"]["eligible_spend"])
        self.assertEqual(1000, result["welcome"]["spend"])

    def test_hsbc_effective_date_does_not_retroactively_apply_provisional_mapping(self):
        alerts = [
            {"date": "2026-07-25", "amount": 1000, "merchant": "UTILITY BILL"},
            {"date": "2026-07-26", "amount": 1000, "merchant": "UTILITY BILL"},
        ]
        result = tracker.calculate_benefits(self.config(), alerts, as_of=date(2026, 7, 27))
        self.assertEqual(1000, result["benefits"]["1.5% Other Eligible Spends"]["spend"])
        provisional = result["benefits"]["10% Shopping and Utilities (Provisional)"]
        self.assertEqual(1000, provisional["spend"])
        self.assertTrue(provisional["provisional"])

    def test_new_policy_uses_one_shared_cap_without_retroactive_reclassification(self):
        config = self.modern_config()
        alerts = [
            {"date": "2026-07-25", "amount": 1000, "merchant": "UTILITY BILL", "mcc": "4900", "message_id": "old"},
            {"date": "2026-07-26", "amount": 8000, "merchant": "UTILITY BILL", "mcc": "4900", "message_id": "utility"},
            {"date": "2026-07-27", "amount": 8000, "merchant": "ELECTRONICS STORE", "mcc": "5732", "message_id": "shopping"},
        ]

        result = tracker.calculate_benefits(config, alerts, as_of=date(2026, 7, 27))

        self.assertEqual("2026-07-26", result["policy"]["version"])
        self.assertEqual(1200, result["shared_cap"]["cap"])
        self.assertEqual(1200, result["shared_cap"]["earned"])
        self.assertEqual(0, result["shared_cap"]["remaining"])
        self.assertEqual(
            {"Dining and food delivery", "Grocery", "Shopping", "Utilities", "1.5% Other Eligible Spends"},
            set(result["benefits"]),
        )
        self.assertEqual(1000, result["benefits"]["1.5% Other Eligible Spends"]["spend"])
        self.assertEqual(15, result["benefits"]["1.5% Other Eligible Spends"]["earned"])
        self.assertEqual(800, result["benefits"]["Utilities"]["earned"])
        self.assertEqual(400, result["benefits"]["Shopping"]["earned"])

    def test_new_policy_applies_mcc_exclusions_and_time_bounded_merchant_overrides(self):
        alerts = [
            {"date": "2026-07-26", "amount": 1000, "merchant": "AMAZON MARKETPLACE", "mcc": "5732", "message_id": "amazon-shopping"},
            {"date": "2026-07-26", "amount": 1000, "merchant": "AMAZON FRESH", "mcc": "5411", "message_id": "amazon-grocery"},
            {"date": "2026-07-27", "amount": 1000, "merchant": "MYNTRA", "mcc": "5732", "message_id": "myntra"},
            {"date": "2026-07-27", "amount": 1000, "merchant": "CITY HOSPITAL", "mcc": "8062", "message_id": "hospital"},
            {"date": "2026-07-27", "amount": 1000, "merchant": "OVERSEAS RESTAURANT", "mcc": "5812", "currency": "USD", "message_id": "international"},
            {"date": "2026-07-27", "amount": 1000, "merchant": "UNKNOWN MERCHANT", "message_id": "unknown"},
        ]

        result = tracker.calculate_benefits(self.modern_config(), alerts, as_of=date(2026, 7, 27))
        by_id = {row["message_id"]: row for row in result["classified_transactions"]}

        self.assertEqual(("1.5% Other Eligible Spends", 0.015), (by_id["amazon-shopping"]["category"], by_id["amazon-shopping"]["rate"]))
        self.assertEqual(("Grocery", 0.10), (by_id["amazon-grocery"]["category"], by_id["amazon-grocery"]["rate"]))
        self.assertEqual(("Shopping", 0.10), (by_id["myntra"]["category"], by_id["myntra"]["rate"]))
        self.assertEqual(("Excluded", 0.0), (by_id["hospital"]["category"], by_id["hospital"]["rate"]))
        self.assertEqual(("Excluded", 0.0), (by_id["international"]["category"], by_id["international"]["rate"]))
        self.assertEqual(("Unclassified", 0.0), (by_id["unknown"]["category"], by_id["unknown"]["rate"]))
        self.assertEqual(15, result["benefits"]["1.5% Other Eligible Spends"]["earned"])
        self.assertEqual(200, result["shared_cap"]["earned"])

    def test_period_totals_deduplicate_reversals_and_leave_unclassified_spend_unrewarded(self):
        alerts = [
            {"date": "2026-07-27", "amount": 1000, "merchant": "GROCERY", "mcc": "5411", "message_id": "prior-cycle"},
            {"date": "2026-07-29", "amount": 2000, "merchant": "UTILITY", "mcc": "4900", "message_id": "current-utility"},
            {"date": "2026-07-29", "amount": 2000, "merchant": "UTILITY", "mcc": "4900", "message_id": "current-utility"},
            {"date": "2026-07-30", "amount": 500, "merchant": "UNKNOWN", "message_id": "unknown"},
            {"date": "2026-07-30", "amount": 3000, "merchant": "ELECTRONICS", "mcc": "5732", "message_id": "reversed-purchase"},
            {"date": "2026-08-01", "amount": 3000, "merchant": "ELECTRONICS REVERSAL", "transaction_type": "reversal", "reversal_of": "reversed-purchase", "message_id": "reversal"},
        ]

        result = tracker.calculate_benefits(self.modern_config(), alerts, as_of=date(2026, 8, 1))

        self.assertEqual(3500, result["period_totals"]["spend"]["lifetime"])
        self.assertEqual(2500, result["period_totals"]["spend"]["current_cycle"])
        self.assertEqual(300, result["period_totals"]["cashback"]["lifetime"])
        self.assertEqual(200, result["period_totals"]["cashback"]["current_cycle"])
        self.assertEqual(500, result["unclassified"]["spend"])
        self.assertEqual(1, result["unclassified"]["transactions"])
        self.assertEqual(2500, result["total_spend"])
        self.assertEqual(3500, result["annual_fee"]["eligible_spend"])
        self.assertEqual(1000, result["welcome"]["spend"])

    def test_fuel_offer_and_lounge_entitlements_use_their_own_windows(self):
        alerts = [
            {"date": "2026-09-02", "amount": 5000, "merchant": "FUEL ONE", "mcc": "5541", "is_contactless": True, "country": "IN", "message_id": "fuel-1"},
            {"date": "2026-09-03", "amount": 5000, "merchant": "FUEL TWO", "mcc": "5542", "is_contactless": True, "country": "IN", "message_id": "fuel-2"},
            {"date": "2026-09-04", "amount": 999, "merchant": "FUEL SMALL", "mcc": "5541", "is_contactless": True, "country": "IN", "message_id": "fuel-small"},
            {"date": "2026-09-05", "amount": 2000, "merchant": "FUEL CHIP", "mcc": "5541", "is_contactless": False, "country": "IN", "message_id": "fuel-chip"},
            {"date": "2026-09-06", "amount": 5001, "merchant": "FUEL LARGE", "mcc": "5541", "is_contactless": True, "country": "IN", "message_id": "fuel-large"},
        ]

        result = tracker.calculate_benefits(self.modern_config(), alerts, as_of=date(2026, 9, 15))
        fuel = result["limited_offers"]["fuel"]

        self.assertEqual(10000, fuel["progress"])
        self.assertEqual(10000, fuel["target"])
        self.assertEqual(250, fuel["reward"])
        self.assertEqual("Met", fuel["status"])
        self.assertEqual("2026-09-30", fuel["deadline"])
        self.assertTrue(fuel["source_conflict"])
        self.assertEqual(
            [
                {"id": "domestic-h1", "allowance": 1, "used": None, "available": False},
                {"id": "domestic-h2", "allowance": 1, "used": None, "available": True},
                {"id": "international", "allowance": 1, "used": None, "available": True},
            ],
            [
                {key: row[key] for key in ("id", "allowance", "used", "available")}
                for row in result["entitlements"]["lounges"]
            ],
        )

    def test_myntra_temporary_acceleration_expires_after_october(self):
        result = tracker.calculate_benefits(
            self.modern_config(),
            [{"date": "2026-11-01", "amount": 1000, "merchant": "MYNTRA", "mcc": "5732", "message_id": "myntra-expired"}],
            as_of=date(2026, 11, 1),
        )
        transaction = result["classified_transactions"][0]
        self.assertEqual("1.5% Other Eligible Spends", transaction["category"])
        self.assertEqual(0.015, transaction["rate"])
        self.assertEqual(15, result["benefits"]["1.5% Other Eligible Spends"]["earned"])
        self.assertEqual(0, result["shared_cap"]["earned"])

    def test_modern_dashboard_summary_publishes_validated_shared_cap_and_benefit_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            alerts = [
                {"date": "2026-07-29", "amount": 1000, "merchant": "UTILITY", "mcc": "4900", "message_id": "utility"},
                {"date": "2026-07-30", "amount": 500, "merchant": "UNKNOWN", "message_id": "unknown"},
            ]
            (root / "benefits_config.json").write_text(json.dumps(self.modern_config()))
            (root / "gmail_alerts.json").write_text(json.dumps(alerts))
            (root / "sync_metadata.json").write_text(json.dumps({
                "run_id": "modern-run", "alert_count": 2, "unique_alert_count": 2,
                "cached_total": 1500, "source": "gmail-api", "synced_at": "2026-07-30T10:00:00Z",
                "latest_alert_date": "2026-07-30",
            }))
            (root / "validation_report.json").write_text(json.dumps({
                "ok": True, "run_id": "modern-run", "alert_count": 2,
            }))

            tracker.write_report(root, as_of=date(2026, 7, 30))
            summary = json.loads((root / "dashboard_summary.json").read_text())

            self.assertEqual(2, summary["schema_version"])
            self.assertEqual("2026-07-26", summary["policy"]["version"])
            self.assertEqual(1200, summary["shared_cap"]["cap"])
            self.assertEqual(100, summary["shared_cap"]["earned"])
            self.assertEqual(1100, summary["shared_cap"]["remaining"])
            self.assertEqual(1500, summary["period_totals"]["spend"]["current_cycle"])
            self.assertEqual(500, summary["unclassified"]["spend"])
            self.assertEqual(1, summary["unclassified"]["transactions"])
            self.assertEqual(10000, summary["limited_offers"]["fuel"]["target"])
            self.assertEqual(3, len(summary["entitlements"]["lounges"]))
            self.assertEqual(20000, summary["welcome"]["target"])
            report = (root / "benefit_tracker_report.md").read_text()
            self.assertIn("Shared 10% cashback cap", report)
            self.assertIn("Policy version: 2026-07-26", report)
            self.assertIn("Needs MCC evidence: INR 500.00 across 1 transaction", report)
            self.assertIn("Contactless fuel offer", report)
            self.assertIn("Lounge entitlements", report)
            self.assertNotIn("Shopping and Utilities (Provisional)", report)

    def test_atomic_dashboard_summary_matches_sync_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "benefits_config.json").write_text(json.dumps(self.config()))
            (root / "gmail_alerts.json").write_text(json.dumps([{"date": "2026-07-01", "amount": 500, "merchant": "ZOMATO"}]))
            (root / "sync_metadata.json").write_text(json.dumps({"run_id": "r1", "alert_count": 1, "unique_alert_count": 1, "cached_total": 500}))
            (root / "validation_report.json").write_text(json.dumps({"ok": True, "run_id": "r1", "alert_count": 1}))
            tracker.write_report(root, as_of=date(2026, 7, 2))
            summary = json.loads((root / "dashboard_summary.json").read_text())
            self.assertEqual("r1", summary["run_id"])
            self.assertEqual(1, summary["schema_version"])
            accelerated = next(item for item in summary["benefits"] if item["name"] == "10% Dining, Food Delivery and Grocery")
            uncapped = next(item for item in summary["benefits"] if item["name"] == "1.5% Other Eligible Spends")
            self.assertEqual(1200, accelerated["cap"])
            self.assertIsInstance(accelerated["spend"], (int, float))
            self.assertIsInstance(accelerated["earned"], (int, float))
            self.assertIsNone(uncapped["cap"])
            self.assertIsNone(uncapped["remaining"])
            self.assertIsInstance(uncapped["spend"], (int, float))
            self.assertIsInstance(uncapped["earned"], (int, float))
            self.assertEqual("2026-06-29", summary["annual_fee"]["period_start"])
            self.assertEqual("2027-06-28", summary["annual_fee"]["period_end"])
            welcome = summary["welcome"]
            self.assertEqual(1000, welcome["reward"])
            self.assertEqual("2026-06-29", welcome["activation_date"])
            self.assertEqual("2026-07-29", welcome["deadline"])
            self.assertEqual("provisional", welcome["evidence_state"])
            self.assertEqual(
                "Supported by HSBC app setup and PIN reset.",
                welcome["evidence_source"],
            )

    def test_two_run_lifecycle_allows_old_summary_then_publishes_current_triad(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "benefits_config.json").write_text(json.dumps(self.config()))
            for run_id, alerts in (("r1", []), ("r2", [{"date": "2026-07-01", "amount": 500, "merchant": "ZOMATO"}])):
                (root / "gmail_alerts.json").write_text(json.dumps(alerts))
                (root / "sync_metadata.json").write_text(json.dumps({"run_id": run_id, "alert_count": len(alerts), "unique_alert_count": len(alerts), "cached_total": sum(a["amount"] for a in alerts), "synced_at": "2099-01-01T00:00:00Z", "source": "gmail-api", "message_ids_seen": []}))
                validation = tracker.validate_card_dir(root)
                self.assertTrue(validation["ok"])
                self.assertEqual(run_id, validation["run_id"])
                tracker.write_report(root, as_of=date(2026, 7, 2))
                self.assertEqual(run_id, json.loads((root / "dashboard_summary.json").read_text())["run_id"])
            metadata = json.loads((root / "sync_metadata.json").read_text())
            validation = json.loads((root / "validation_report.json").read_text())
            summary = json.loads((root / "dashboard_summary.json").read_text())
            self.assertEqual({"r2"}, {metadata["run_id"], validation["run_id"], summary["run_id"]})

    def test_inconsistent_current_validation_does_not_replace_summary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "benefits_config.json").write_text(json.dumps(self.config()))
            (root / "gmail_alerts.json").write_text("[]")
            (root / "sync_metadata.json").write_text(json.dumps({"run_id": "r2", "alert_count": 0}))
            old = {"run_id": "r1", "alert_count": 1}
            (root / "dashboard_summary.json").write_text(json.dumps(old))
            (root / "validation_report.json").write_text(json.dumps({"ok": True, "run_id": "wrong", "alert_count": 0}))
            with self.assertRaisesRegex(ValueError, "validation_report"):
                tracker.write_report(root, as_of=date(2026, 7, 2))
            self.assertEqual(old, json.loads((root / "dashboard_summary.json").read_text()))

    def test_missing_welcome_evidence_fails_before_atomic_publication(self):
        for missing_field in (
            "activation_proxy_date",
            "window_days",
            "evidence_state",
            "activation_proxy_source",
        ):
            with self.subTest(missing_field=missing_field), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                config = self.config()
                del config["welcome"][missing_field]
                (root / "benefits_config.json").write_text(json.dumps(config))
                (root / "gmail_alerts.json").write_text("[]")
                (root / "sync_metadata.json").write_text(json.dumps({
                    "run_id": "r2", "alert_count": 0, "unique_alert_count": 0,
                }))
                (root / "validation_report.json").write_text(json.dumps({
                    "ok": True, "run_id": "r2", "alert_count": 0,
                }))
                prior_bytes = b'{"run_id":"r1","sentinel":"exact bytes"}\n'
                (root / "dashboard_summary.json").write_bytes(prior_bytes)

                with self.assertRaisesRegex(ValueError, "HSBC welcome evidence is incomplete"):
                    tracker.write_report(root, as_of=date(2026, 7, 2))

                self.assertEqual(prior_bytes, (root / "dashboard_summary.json").read_bytes())

    def test_malformed_generated_payload_fails_final_gate_and_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "benefits_config.json").write_text(json.dumps(self.config()))
            (root / "gmail_alerts.json").write_text("[]")
            (root / "sync_metadata.json").write_text(json.dumps({"run_id": "r2", "alert_count": 0, "unique_alert_count": 0}))
            (root / "validation_report.json").write_text(json.dumps({"ok": True, "run_id": "r2", "alert_count": 0}))
            prior_bytes = b'{"run_id":"r1","sentinel":"exact bytes"}\n'
            (root / "dashboard_summary.json").write_bytes(prior_bytes)
            malformed = {"run_id": "corrupt", "alert_count": 99}
            with mock.patch.object(tracker, "build_dashboard_summary", return_value=malformed):
                with self.assertRaisesRegex(ValueError, "dashboard payload"):
                    tracker.write_report(root, as_of=date(2026, 7, 2))
            self.assertEqual(prior_bytes, (root / "dashboard_summary.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
