import importlib.util
from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import card_benefit_tracker as tracker


def hdfc_config():
    return {
        "card_name": "HDFC Diners Black Metal Credit Card",
        "welcome": {"activation_proxy_date": "2026-06-30"},
        "reward_model": {
            "base_points_per_150": 5,
            "accelerated_multiplier": 4,
            "accelerated_monthly_cap": 10000,
            "confirmed_statement": {
                "through": "2026-07-13",
                "total_points": 8848,
                "base_points": 4245,
                "accelerated_points": 4600,
                "bonus_points": 3,
            },
            "smartbuy_classifications": {
                "yatra": {"message_id": "yatra", "classification": "SmartBuy flight", "evidence": "confirmed", "reward_eligible": True, "accelerated_multiplier": 4},
                "emt": {"message_id": "emt", "classification": "SmartBuy flight", "evidence": "confirmed", "reward_eligible": True, "accelerated_multiplier": 4},
                "jockey": {"message_id": "jockey", "classification": "SmartBuy 10X partner", "evidence": "confirmed", "reward_eligible": True, "accelerated_multiplier": 9},
            },
        },
    }


def alert(message_id, amount, when, merchant="Ordinary merchant"):
    return {"message_id": message_id, "amount": amount, "date": when[:10], "email_date": when, "merchant": merchant}


class HdfcRewardSummaryTests(unittest.TestCase):
    def test_lifetime_points_add_only_post_statement_transaction_estimates_without_resetting_confirmed_history(self):
        summary = tracker.calculate_hdfc_reward_summary(
            hdfc_config(),
            [
                alert("old", 300, "2026-07-12T12:00:00+05:30"),
                alert("emt", 19792, "2026-07-15T20:05:19+05:30", "EMT FLIGHT VIA SMARTBU"),
            ],
            date(2026, 7, 26),
        )
        self.assertEqual(20092, summary["lifetime_spend"])
        self.assertEqual(
            {"total": 12123, "base": 4900, "accelerated": 7220, "bonus": 3},
            {key: summary["lifetime_points"][key] for key in ("total", "base", "accelerated", "bonus")},
        )
        self.assertEqual("mixed", summary["lifetime_points"]["evidence_status"])

    def test_points_round_each_eligible_transaction_down_to_150_blocks_and_only_allowlisted_smartbuy_earns_acceleration(self):
        summary = tracker.calculate_hdfc_reward_summary(
            hdfc_config(),
            [
                alert("ordinary", 299, "2026-07-15T09:00:00+05:30", "SOMETHING VIA SMARTBUY"),
                alert("emt", 151, "2026-07-15T20:05:19+05:30", "EMT FLIGHT VIA SMARTBU"),
            ],
            date(2026, 7, 26),
        )
        self.assertEqual({"base": 5, "accelerated": 20}, summary["post_statement_points"])

    def test_approved_smartbuy_classification_uses_its_transaction_multiplier(self):
        summary = tracker.calculate_hdfc_reward_summary(
            hdfc_config(),
            [
                alert("emt", 150, "2026-07-15T09:00:00+05:30"),
                alert("jockey", 150, "2026-07-16T09:00:00+05:30"),
            ],
            date(2026, 7, 26),
        )
        self.assertEqual({"base": 10, "accelerated": 65}, summary["post_statement_points"])

    def test_load_config_uses_the_statement_artifact_as_the_confirmed_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            card_dir = Path(folder)
            (card_dir / "benefits_config.json").write_text(
                '{"reward_model":{"confirmed_statement_artifact":"statement_rewards.json"}}',
                encoding="utf-8",
            )
            (card_dir / "statement_rewards.json").write_text(
                '{"scope":"lifetime","statement_start":"2026-06-14","statement_end":"2026-07-13",'
                '"total_points":8848,"base_points":4245,"accelerated_points":4600,"bonus_points":3}',
                encoding="utf-8",
            )
            config = tracker.load_config(card_dir)
        self.assertEqual("2026-07-13", config["reward_model"]["confirmed_statement"]["through"])
        self.assertEqual(8848, config["reward_model"]["confirmed_statement"]["total_points"])

    def test_calendar_month_cap_combines_confirmed_july_smartbuy_and_post_statement_estimate_then_resets_in_ist(self):
        summary = tracker.calculate_hdfc_reward_summary(
            hdfc_config(),
            [
                alert("yatra", 24334, "2026-07-08T13:02:59+05:30", "YATRA FLIGHT VIA SMART"),
                alert("emt", 19792, "2026-07-15T20:05:19+05:30", "EMT FLIGHT VIA SMARTBU"),
            ],
            date(2026, 7, 26),
        )["accelerated_cap"]
        self.assertEqual({"cap": 10000, "earned": 5860, "remaining": 4140, "remaining_percent": 41.4}, {key: summary[key] for key in ("cap", "earned", "remaining", "remaining_percent")})
        self.assertEqual("2026-07-01", summary["month_start"])
        self.assertEqual("2026-07-31", summary["month_end"])
        self.assertEqual("2026-08-01", summary["reset_date"])
        self.assertEqual(5, summary["days_remaining"])
        self.assertEqual("mixed", summary["evidence_status"])

    def test_cap_clamps_remaining_at_zero_when_estimated_accelerated_points_exceed_the_monthly_limit(self):
        config = hdfc_config()
        config["reward_model"].pop("confirmed_statement")
        summary = tracker.calculate_hdfc_reward_summary(
            config,
            [alert("emt", 600000, "2026-07-15T09:00:00+05:30")],
            date(2026, 7, 31),
        )["accelerated_cap"]
        self.assertEqual(10000, summary["earned"])
        self.assertEqual(0, summary["remaining"])
        self.assertEqual(0.0, summary["remaining_percent"])
        self.assertEqual("estimated", summary["evidence_status"])
        self.assertEqual(10000, tracker.calculate_hdfc_reward_summary(
            config,
            [alert("emt", 600000, "2026-07-15T09:00:00+05:30")],
            date(2026, 7, 31),
        )["lifetime_points"]["accelerated"])

    def test_unclassified_post_statement_transaction_does_not_receive_base_points(self):
        summary = tracker.calculate_hdfc_reward_summary(
            hdfc_config(),
            [alert("ordinary", 300, "2026-07-15T09:00:00+05:30")],
            date(2026, 7, 26),
        )
        self.assertEqual({"base": 0, "accelerated": 0}, summary["post_statement_points"])

    def test_cap_reports_unavailable_without_statement_or_allowlisted_smartbuy_evidence(self):
        config = hdfc_config()
        config["reward_model"].pop("confirmed_statement")
        config["reward_model"]["smartbuy_classifications"] = {}
        summary = tracker.calculate_hdfc_reward_summary(
            config,
            [alert("ordinary", 600000, "2026-07-15T09:00:00+05:30")],
            date(2026, 7, 31),
        )["accelerated_cap"]
        self.assertEqual("unavailable", summary["evidence_status"])


if __name__ == "__main__":
    unittest.main()
