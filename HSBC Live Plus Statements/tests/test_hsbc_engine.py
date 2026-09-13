import unittest
from datetime import date, timedelta
from pathlib import Path
import sys

ENGINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_DIR))

import hsbc_engine


class TestHSBCEngine(unittest.TestCase):
    def setUp(self):
        self.card_dir = ENGINE_DIR

    def test_billing_cycle_mid_cycle(self):
        # 12 Sep 2026 -> reference day <= 13
        # Should be cycle: 14 Aug 2026 to 13 Sep 2026, 1 day remaining
        ref = date(2026, 9, 12)
        start, end, days = hsbc_engine.get_billing_cycle(ref, cycle_day=13)
        self.assertEqual(start, date(2026, 8, 14))
        self.assertEqual(end, date(2026, 9, 13))
        self.assertEqual(days, 1)

    def test_billing_cycle_end_day(self):
        # 13 Sep 2026 -> last day of cycle (cycle_day=13)
        # Should be cycle: 14 Aug 2026 to 13 Sep 2026, 0 days remaining -> "Resets Today"
        ref = date(2026, 9, 13)
        start, end, days = hsbc_engine.get_billing_cycle(ref, cycle_day=13)
        self.assertEqual(start, date(2026, 8, 14))
        self.assertEqual(end, date(2026, 9, 13))
        self.assertEqual(days, 0)

        data = hsbc_engine.compute_hsbc_dashboard_data(self.card_dir, today=ref)
        self.assertEqual(data["cycle"]["days_remaining"], 0)
        self.assertEqual(data["cycle"]["reset_str"], "Resets Today")

    def test_billing_cycle_post_cycle(self):
        # 14 Sep 2026 -> reference day > 13
        # Should be cycle: 14 Sep 2026 to 13 Oct 2026
        ref = date(2026, 9, 14)
        start, end, days = hsbc_engine.get_billing_cycle(ref, cycle_day=13)
        self.assertEqual(start, date(2026, 9, 14))
        self.assertEqual(end, date(2026, 10, 13))
        self.assertEqual(days, 29)

    def test_mcc_matching_confirmed_merchants(self):
        registry = {
            "merchants": {
                "SWIGGY": {"mcc": "5812", "category": "Dining and food delivery", "eligible_10_percent": True, "source": "Reddit r/CreditCardsIndia"},
                "BLINKIT": {"mcc": "5411", "category": "Grocery", "eligible_10_percent": True, "source": "TechnoFino Community"},
                "AMAZON": {"mcc": "5311", "category": "General E-Commerce", "eligible_10_percent": False, "source": "Official HSBC Policy"},
            }
        }
        policy = {"accelerated_rate": 0.10, "standard_rate": 0.015}

        # Test Swiggy -> 10% confirmed
        res_swiggy = hsbc_engine.match_mcc_and_category("RAZ*SWIGGY E COMMERCE", registry, policy)
        self.assertEqual(res_swiggy["mcc"], "5812")
        self.assertTrue(res_swiggy["is_accelerated"])
        self.assertEqual(res_swiggy["rate"], 0.10)
        self.assertEqual(res_swiggy["evidence"], "confirmed")

        # Test Blinkit -> 10% confirmed
        res_blink = hsbc_engine.match_mcc_and_category("BLINKIT GURGAON", registry, policy)
        self.assertEqual(res_blink["mcc"], "5411")
        self.assertTrue(res_blink["is_accelerated"])
        self.assertEqual(res_blink["rate"], 0.10)

        # Test Amazon -> 1.5% base
        res_amzn = hsbc_engine.match_mcc_and_category("AMAZON PAY INDIA", registry, policy)
        self.assertFalse(res_amzn["is_accelerated"])
        self.assertEqual(res_amzn["rate"], 0.015)

    def test_mcc_keyword_inference(self):
        registry = {"merchants": {}}
        policy = {"accelerated_rate": 0.10, "standard_rate": 0.015}

        # New unmapped restaurant
        res_cafe = hsbc_engine.match_mcc_and_category("BLUE TOKAI COFFEE ROASTERS", registry, policy)
        self.assertEqual(res_cafe["rate"], 0.015)

        # Keyword dining
        res_food = hsbc_engine.match_mcc_and_category("DELHI FOOD COURT DINING", registry, policy)
        self.assertTrue(res_food["is_accelerated"])
        self.assertEqual(res_food["evidence"], "estimated")

    def test_compute_hsbc_dashboard_data(self):
        data = hsbc_engine.compute_hsbc_dashboard_data(self.card_dir, today=date(2026, 9, 12))
        self.assertEqual(data["card_ending"], "8690")
        self.assertEqual(data["cashback_cap"]["cap_limit"], 1200.0)
        self.assertIn("current_cycle", data["transactions"])
        self.assertIn("all", data["transactions"])
        self.assertGreater(len(data["transactions"]["all"]), 0)


if __name__ == "__main__":
    unittest.main()
