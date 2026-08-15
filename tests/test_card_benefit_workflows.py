import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import card_benefit_tracker as tracker
import card_freshness
import build_combined_card_benefits_report as combined


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class BenefitCalculationTests(unittest.TestCase):
    def test_statement_confirmed_cycle_rolls_from_the_latest_statement_close(self):
        config = {
            "card_name": "HDFC Diners Black Metal Credit Card",
            "cycle": {
                "start": "2026-06-14",
                "end": "2026-07-13",
                "evidence_status": "confirmed",
                "source": "HDFC statement dated 13 July 2026",
            },
        }

        start, end = tracker.cycle_window(config, tracker.parse_date("2026-08-02"))

        self.assertEqual("2026-07-14", start.isoformat())
        self.assertEqual("2026-08-13", end.isoformat())

    def test_dashboard_summary_preserves_statement_cycle_evidence(self):
        config = {
            "card_name": "HDFC Diners Black Metal Credit Card",
            "card_ending": "2360",
            "variant_status": "confirmed",
            "cycle": {
                "start": "2026-06-14",
                "end": "2026-07-13",
                "evidence_status": "confirmed",
                "source": "HDFC statement dated 13 July 2026",
                "statement_date": "2026-07-13",
            },
            "annual_fee": {},
            "welcome": {},
            "benefit_rules": [],
            "benefits": [],
        }
        summary = {
            "card_name": config["card_name"],
            "card_ending": "2360",
            "cycle_start": "2026-07-14",
            "cycle_end": "2026-08-13",
            "total_spend": 0,
            "benefits": {},
            "annual_fee": {},
            "welcome": {},
            "variant_status": "confirmed",
        }

        payload = tracker.build_dashboard_summary(config, summary, {"run_id": "run-1"}, 0)

        self.assertEqual(
            {
                "start": "2026-07-14",
                "end": "2026-08-13",
                "spend": 0,
                "evidence_status": "confirmed",
                "source": "HDFC statement dated 13 July 2026",
                "statement_date": "2026-07-13",
            },
            payload["cycle"],
        )

    def test_hdfc_dashboard_summary_includes_rewards_milestones_and_evidence(self):
        config = {
            "card_name": "HDFC Diners Black Metal Credit Card",
            "card_ending": "2360",
            "variant_status": "confirmed",
            "benefits": ["Unlimited airport lounge access", "6 complimentary golf games per quarter"],
            "reward_model": {"base_points_per_150": 5},
            "annual_fee": {"evidence_state": "provisional"},
            "welcome": {
                "spend_target": 150000,
                "window_days": 90,
                "evidence_state": "provisional",
                "activation_proxy_date": "2026-06-30",
                "activation_proxy_source": "MyCards control change followed by successful card usage",
                "memberships": ["Club Marriott", "Amazon Prime", "Swiggy One"],
            },
            "quarterly_bonus": {"spend_target": 400000, "bonus_points": 10000},
            "benefit_rules": [],
        }
        summary = {
            "card_name": config["card_name"], "card_ending": "2360",
            "cycle_start": "2026-06-29", "cycle_end": "2026-07-28", "total_spend": 129318,
            "benefits": {}, "annual_fee": {"progress": 129318, "target": 800000},
            "welcome": {"spend": 129318, "target": 150000},
            "quarterly_bonus": {"spend": 119002, "target": 400000, "bonus_points": 10000},
            "reward_points": {"base_points": 4310, "smartbuy_value": 4310, "airmile_value": 4310,
                              "voucher_value": 2155, "cashback_value": 1293},
            "variant_status": "confirmed",
        }
        metadata = {"run_id": "hdfc-run-1"}

        payload = tracker.build_dashboard_summary(config, summary, metadata, 7)

        self.assertEqual(summary["reward_points"], payload["rewards"])
        self.assertEqual(summary["quarterly_bonus"], payload["quarterly_bonus"])
        self.assertEqual(["Club Marriott", "Amazon Prime", "Swiggy One"], payload["welcome"]["memberships"])
        self.assertEqual("2026-06-30", payload["welcome"]["activation_proxy_date"])
        self.assertEqual("provisional", payload["annual_fee"]["evidence_state"])
        self.assertIn("Unlimited airport lounge access", payload["evergreen_benefits"])

    def test_hdfc_calculation_tracks_calendar_quarter_bonus_progress(self):
        config = {
            "card_name": "HDFC Diners Black Metal Credit Card", "card_ending": "2360",
            "variant_status": "confirmed", "cycle": {"start": "2026-06-29", "end": "2026-07-28"},
            "annual_fee": {"waiver_spend": 800000},
            "quarterly_bonus": {"spend_target": 400000, "bonus_points": 10000},
            "benefit_rules": [],
        }
        alerts = [
            {"date": "2026-06-30", "amount": 10000, "merchant": "Prior quarter"},
            {"date": "2026-07-01", "amount": 120000, "merchant": "Current quarter"},
        ]

        summary = tracker.calculate_benefits(config, alerts, as_of=tracker.parse_date("2026-07-15"))

        self.assertEqual(120000, summary["quarterly_bonus"]["spend"])
        self.assertEqual(400000, summary["quarterly_bonus"]["target"])
        self.assertEqual(280000, summary["quarterly_bonus"]["remaining"])
        self.assertEqual("2026-07-01", summary["quarterly_bonus"]["period_start"])
        self.assertEqual("2026-09-30", summary["quarterly_bonus"]["deadline"])
        self.assertEqual(10000, summary["quarterly_bonus"]["bonus_points"])

    def test_hsbc_live_plus_caps_accelerated_cashback_and_tracks_welcome_spend(self):
        config = {
            "card_name": "HSBC Live+ Credit Card",
            "card_ending": "8690",
            "issuer": "HSBC India",
            "variant_status": "confirmed",
            "cycle": {"start": "2026-06-30", "end": "2026-07-30"},
            "annual_fee": {"amount": 999, "waiver_spend": 200000},
            "welcome": {"spend_target": 20000, "window_days": 30},
            "benefit_rules": [
                {"name": "Accelerated", "rate": 0.10, "monthly_cap": 1000, "match": ["BLINK", "ZOMATO"]},
                {"name": "Base", "rate": 0.015, "monthly_cap": None, "match": ["DEFAULT"]},
            ],
        }
        alerts = [
            {"date": "30/06/2026", "amount": 9000, "subject": "HSBC 8690 at BLINK COMMERCE"},
            {"date": "01/07/2026", "amount": 4000, "subject": "HSBC 8690 at ZOMATO"},
            {"date": "01/07/2026", "amount": 10000, "subject": "HSBC 8690 at HOTEL"},
        ]

        summary = tracker.calculate_benefits(config, alerts, as_of=tracker.parse_date("01/07/2026"))

        accelerated = summary["benefits"]["Accelerated"]
        base = summary["benefits"]["Base"]
        self.assertEqual(13000, accelerated["spend"])
        self.assertEqual(1000, accelerated["earned"])
        self.assertEqual(10000, base["spend"])
        self.assertEqual(150, base["earned"])
        self.assertEqual(23000, summary["welcome"]["spend"])
        self.assertEqual("Met", summary["welcome"]["status"])

    def test_hdfc_tracks_points_value_and_waiver_without_cashback_cap(self):
        config = {
            "card_name": "HDFC Diners Black Metal Credit Card",
            "card_ending": "2360",
            "issuer": "HDFC Bank",
            "variant_status": "confirmed",
            "cycle": {"start": "2026-06-30", "end": "2026-07-30"},
            "annual_fee": {"amount": 10000, "waiver_spend": 800000},
            "reward_model": {"base_points_per_150": 5, "smartbuy_value_per_point": 1.0, "cashback_value_per_point": 0.30},
            "benefit_rules": [
                {"name": "Eligible Rewards", "rate": 0, "monthly_cap": None, "match": ["DEFAULT"]}
            ],
        }
        alerts = [{"date": "30/06/2026", "amount": 10316, "subject": "HDFC 2360 at GOIBIBO FLIGHT VIA SMA"}]

        summary = tracker.calculate_benefits(config, alerts, as_of=tracker.parse_date("01/07/2026"))

        self.assertEqual(10316, summary["total_spend"])
        self.assertEqual(340, summary["reward_points"]["base_points"])
        self.assertEqual(340, summary["reward_points"]["smartbuy_value"])
        self.assertEqual(102, summary["reward_points"]["cashback_value"])
        self.assertEqual(789684, summary["annual_fee"]["remaining_spend_for_waiver"])

    def test_hdfc_report_sorts_current_cycle_transactions_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = Path(tmp) / "HDFC Diners Black Metal Statements"
            write_json(card_dir / "benefits_config.json", {
                "card_name": "HDFC Diners Black Metal Credit Card",
                "card_ending": "2360",
                "issuer": "HDFC Bank",
                "variant_status": "confirmed",
                "transaction_order": "desc",
                "cycle": {"start": "2026-06-29", "end": "2026-07-28"},
                "annual_fee": {"amount": 10000, "waiver_spend": 800000},
                "welcome": {"spend_target": 150000, "window_days": 90},
                "benefit_rules": [],
            })
            write_json(card_dir / "gmail_alerts.json", [
                {"date": "2026-06-30", "amount": 100, "merchant": "Oldest"},
                {"date": "2026-07-13", "amount": 300, "merchant": "Newest"},
                {"date": "2026-07-02", "amount": 200, "merchant": "Middle"},
            ])

            report = tracker.build_report(card_dir, as_of=tracker.parse_date("2026-07-14"))

            self.assertLess(report.index("| 2026-07-13 |"), report.index("| 2026-07-02 |"))
            self.assertLess(report.index("| 2026-07-02 |"), report.index("| 2026-06-30 |"))

    def test_hdfc_fee_waiver_uses_provisional_approval_period(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = Path(tmp) / "HDFC Diners Black Metal Statements"
            write_json(card_dir / "benefits_config.json", {
                "card_name": "HDFC Diners Black Metal Credit Card",
                "card_ending": "2360",
                "issuer": "HDFC Bank",
                "variant_status": "confirmed",
                "cycle": {"start": "2026-06-14", "end": "2026-07-13"},
                "annual_fee": {
                    "amount": 10000,
                    "waiver_spend": 800000,
                    "period_start": "2026-06-25",
                    "period_end": "2027-06-24",
                    "evidence_state": "provisional",
                    "evidence_source": "HDFC approval email dated 25 June 2026.",
                },
                "welcome": {"spend_target": 150000, "window_days": 90},
                "benefit_rules": [],
            })
            write_json(card_dir / "gmail_alerts.json", [
                {"date": "2026-07-01", "amount": 100000, "merchant": "Merchant"},
            ])

            report = tracker.build_report(card_dir, as_of=tracker.parse_date("2026-07-14"))

            self.assertIn("- Period: 2026-06-25 to 2027-06-24", report)
            self.assertIn("- Days left: 345", report)
            self.assertIn("- Evidence: Provisional", report)
            self.assertIn("- Evidence source: HDFC approval email dated 25 June 2026.", report)

    def test_pending_sbi_variant_disables_reward_recommendations(self):
        config = {
            "card_name": "SBI Card ending 3366",
            "card_ending": "3366",
            "issuer": "SBI Card",
            "variant_status": "pending",
            "cycle": {"statement_day": 30},
            "annual_fee": {"amount": None, "waiver_spend": None},
            "benefit_rules": [],
        }

        summary = tracker.calculate_benefits(config, [], as_of=tracker.parse_date("01/07/2026"))

        self.assertEqual("pending", summary["variant_status"])
        self.assertTrue(summary["recommendations_disabled"])
        self.assertIn("variant is not confirmed", summary["recommendation_note"])


class FreshnessGateTests(unittest.TestCase):
    def test_distinct_message_ids_preserve_identical_business_transactions(self):
        alerts = [
            {"message_id": "gmail-1", "date": "2026-07-14", "amount": 499, "merchant": "SAME MERCHANT"},
            {"message_id": "gmail-2", "date": "2026-07-14", "amount": 499, "merchant": "SAME MERCHANT"},
        ]

        self.assertEqual(2, len(card_freshness.unique_alerts(alerts)))
        self.assertEqual(998, card_freshness.alert_total(alerts))

    def test_repeated_message_id_dedupes_even_when_business_fields_differ(self):
        alerts = [
            {"message_id": "gmail-1", "date": "2026-07-14", "amount": 499, "merchant": "FIRST PARSE"},
            {"message_id": "gmail-1", "date": "2026-07-15", "amount": 599, "merchant": "SECOND PARSE"},
        ]

        self.assertEqual(1, len(card_freshness.unique_alerts(alerts)))

    def test_legacy_alerts_still_dedupe_by_business_fields(self):
        alerts = [
            {"date": "2026-07-14", "amount": 499, "merchant": "Same   Merchant"},
            {"date": "14/07/2026", "amount": "INR 499.00", "merchant": "same merchant"},
        ]

        self.assertEqual(1, len(card_freshness.unique_alerts(alerts)))

    def test_normalize_alert_preserves_source_metadata_without_nesting_raw(self):
        original = {
            "message_id": "gmail-1",
            "email_date": "2026-07-14T12:30:00Z",
            "source": "gmail-api",
            "date": "2026-07-14",
            "amount": 499,
            "merchant": "Merchant",
        }

        normalized = tracker.normalize_alert(original)
        normalized_again = tracker.normalize_alert(normalized)

        self.assertEqual("gmail-1", normalized_again["message_id"])
        self.assertEqual("2026-07-14T12:30:00Z", normalized_again["email_date"])
        self.assertEqual("gmail-api", normalized_again["source"])
        self.assertIs(original, normalized_again["raw"])

    def test_missing_sync_metadata_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = Path(tmp) / "HSBC Live Plus Statements"
            write_json(card_dir / "gmail_alerts.json", [{"date": "30/06/2026", "amount": 251, "subject": "HSBC 8690 at BLINK"}])

            result = card_freshness.validate_freshness(card_dir, card_name="HSBC Live+")

            self.assertFalse(result["ok"])
            self.assertIn("sync_metadata.json is missing", result["failures"][0])

    def test_expected_app_total_mismatch_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = Path(tmp) / "HSBC Live Plus Statements"
            alerts = [{"date": "30/06/2026", "amount": 251, "subject": "HSBC 8690 at BLINK"}]
            write_json(card_dir / "gmail_alerts.json", alerts)
            card_freshness.write_sync_metadata(
                card_dir,
                card_name="HSBC Live+",
                card_ending="8690",
                source="gmail-api",
                query="HSBC 8690",
                alerts=alerts,
                message_ids=["m1"],
            )

            result = card_freshness.validate_freshness(card_dir, card_name="HSBC Live+", expected_total=1429)

            self.assertFalse(result["ok"])
            self.assertIn("does not reconcile", result["failures"][0])

    def test_stale_sync_metadata_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = Path(tmp) / "HSBC Live Plus Statements"
            alerts = [{"date": "30/06/2026", "amount": 251, "subject": "HSBC 8690 at BLINK"}]
            write_json(card_dir / "gmail_alerts.json", alerts)
            stale = (datetime.now(timezone.utc) - timedelta(hours=48)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            write_json(card_dir / "sync_metadata.json", {
                "synced_at": stale,
                "source": "gmail-api",
                "unique_alert_count": 1,
                "cached_total": 251.0,
                "message_ids_seen": ["m1"],
            })

            result = card_freshness.validate_freshness(card_dir, card_name="HSBC Live+", max_age_hours=36)

            self.assertFalse(result["ok"])
            self.assertIn("Gmail sync is stale", result["failures"][0])


class ReportShapeTests(unittest.TestCase):
    def test_hdfc_report_uses_progress_bars_for_fee_and_welcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = Path(tmp) / "HDFC Diners Black Metal Statements"
            write_json(card_dir / "benefits_config.json", {
                "card_name": "HDFC Diners Black Metal Credit Card",
                "card_ending": "2360",
                "variant_status": "confirmed",
                "cycle": {"start": "2026-06-29", "end": "2026-07-28"},
                "annual_fee": {"amount": 10000, "waiver_spend": 800000},
                "welcome": {"spend_target": 150000, "window_days": 90},
                "quarterly_bonus": {"spend_target": 400000, "bonus_points": 10000},
                "benefit_rules": [],
            })
            write_json(card_dir / "gmail_alerts.json", [
                {"date": "2026-07-01", "amount": 10000, "subject": "HDFC purchase"}
            ])

            report = tracker.build_report(card_dir, as_of=tracker.parse_date("2026-07-01"))

            bars = [line for line in report.splitlines() if line.startswith("`") and line.endswith("%`")]
            self.assertEqual(3, len(bars))
            self.assertIn("- Progress: INR 10,000.00 of INR 800,000.00", report)
            self.assertIn("- Progress: INR 10,000.00 of INR 150,000.00", report)
            self.assertIn("## 4. Quarterly Bonus Tracker", report)
            self.assertIn("- Progress: INR 10,000.00 of INR 400,000.00", report)
            self.assertEqual(2, report.count("- Days left: Pending"))
            self.assertIn("- Days left: 91", report)
            self.assertNotIn("| Annual waiver target |", report)

    def test_hdfc_welcome_tracker_uses_evidenced_activation_proxy(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = Path(tmp) / "HDFC Diners Black Metal Statements"
            write_json(card_dir / "benefits_config.json", {
                "card_name": "HDFC Diners Black Metal Credit Card",
                "card_ending": "2360",
                "variant_status": "confirmed",
                "cycle": {"start": "2026-06-29", "end": "2026-07-28"},
                "annual_fee": {"amount": 10000, "waiver_spend": 800000},
                "welcome": {
                    "spend_target": 150000,
                    "window_days": 90,
                    "activation_proxy_date": "2026-06-30",
                    "activation_proxy_source": "MyCards control change followed by successful card usage",
                    "evidence_state": "provisional",
                },
                "benefit_rules": [],
            })
            write_json(card_dir / "gmail_alerts.json", [
                {"date": "2026-07-01", "amount": 10000, "subject": "HDFC purchase"}
            ])

            report = tracker.build_report(card_dir, as_of=tracker.parse_date("2026-07-14"))

            self.assertIn("- Period: 2026-06-30 to 2026-09-28", report)
            self.assertIn("- Days left: 76", report)
            self.assertIn("- Evidence: Provisional", report)
            self.assertIn("- Activation proxy: MyCards control change followed by successful card usage", report)

    def test_progress_bar_renders_partial_progress(self):
        bar = tracker.render_progress_bar(3301.13, 20000)

        self.assertEqual("`███░░░░░░░░░░░░░░░░░ 16.5%`", bar)

    def test_progress_bar_caps_completed_progress_at_100_percent(self):
        bar = tracker.render_progress_bar(25000, 20000)

        self.assertEqual("`████████████████████ 100.0%`", bar)

    def test_progress_bar_handles_unavailable_target(self):
        self.assertEqual("`Progress unavailable`", tracker.render_progress_bar(3301.13, None))

    def test_report_contains_required_operational_sections_and_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = Path(tmp) / "HSBC Live Plus Statements"
            write_json(card_dir / "benefits_config.json", {
                "card_name": "HSBC Live+ Credit Card",
                "card_ending": "8690",
                "issuer": "HSBC India",
                "variant_status": "confirmed",
                "cycle": {"statement_day": 30},
                "annual_fee": {"amount": 999, "waiver_spend": 200000},
                "welcome": {"spend_target": 20000, "window_days": 30},
                "benefit_rules": [{"name": "Accelerated", "rate": 0.10, "monthly_cap": 1000, "match": ["BLINK"]}],
                "sources": [{"label": "HSBC official Live+ page", "url": "https://www.hsbc.co.in/credit-cards/products/live-plus/"}],
            })
            write_json(card_dir / "gmail_alerts.json", [{"date": "01/07/2026", "amount": 251, "subject": "HSBC 8690 at BLINK"}])

            report = tracker.build_report(card_dir, as_of=tracker.parse_date("01/07/2026"))

            for heading in [
                "## 1. Executive Summary",
                "## 2. Fee and Waiver Tracker",
                "## 3. Welcome Benefit Tracker",
                "## 4. Current Cycle Transaction Table",
                "## 5. Benefit Utilization and Recommendation",
                "## 6. Source Notes",
            ]:
                self.assertIn(heading, report)
            self.assertIn("https://www.hsbc.co.in/credit-cards/products/live-plus/", report)
            self.assertIn("`░░░░░░░░░░░░░░░░░░░░ 0.1%`", report)
            self.assertIn("`░░░░░░░░░░░░░░░░░░░░ 1.3%`", report)
            self.assertIn("- Progress: INR 251.00 of INR 200,000.00", report)
            self.assertIn("- Progress: INR 251.00 of INR 20,000.00", report)
            self.assertNotIn("| Annual waiver target |", report)
            self.assertNotIn("| Welcome spend target |", report)
            self.assertNotIn("Variant status:", report)
            self.assertNotIn("Cycle source:", report)
            self.assertEqual(2, report.count("- Status: In progress"))
            self.assertEqual(2, report.count("- Days left: Pending"))
            self.assertNotIn("Activation and video-KYC voucher offers", report)

    def test_pending_sbi_report_keeps_deadlines_and_evidence_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = Path(tmp) / "SBI New Card Statements"
            write_json(card_dir / "benefits_config.json", {
                "card_name": "SBI Card ending 3366",
                "card_ending": "3366",
                "variant_status": "pending",
                "cycle": {"start": "2026-06-29", "end": "2026-07-28"},
                "annual_fee": {"amount": None, "waiver_spend": None},
                "welcome": {"spend_target": None, "window_days": None},
                "benefit_rules": [],
            })
            write_json(card_dir / "gmail_alerts.json", [])

            report = tracker.build_report(card_dir, as_of=tracker.parse_date("2026-07-01"))

            self.assertEqual(2, report.count("- Days left: Pending"))
            self.assertEqual(2, report.count("- Evidence: Pending"))

    def test_combined_benefit_report_includes_existing_and_new_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for folder, filename, title in [
                ("SBI Cashback Statements", "cashback_cap_report.md", "# SBI Cashback"),
                ("Airtel Axis Statements", "cashback_cap_report.md", "# Airtel Axis"),
                ("Flipkart Axis Statements", "cashback_cap_report.md", "# Flipkart Axis"),
                ("HSBC Live Plus Statements", "benefit_tracker_report.md", "# HSBC Live+"),
                ("HDFC Diners Black Metal Statements", "benefit_tracker_report.md", "# HDFC Diners"),
                ("SBI New Card Statements", "benefit_tracker_report.md", "# SBI New"),
            ]:
                path = base / folder / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(title + "\n\n## 1. Executive Summary\nReady\n", encoding="utf-8")

            report = combined.build_report(base)

            self.assertIn("HSBC Live+", report)
            self.assertIn("HDFC Diners Black Metal", report)
            self.assertIn("SBI New Card", report)
            self.assertIn("SBI Cashback", report)
            self.assertIn("combined card benefits", report.lower())


if __name__ == "__main__":
    unittest.main()
