from datetime import date
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
CARD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CARD_DIR))

import dcbm_engine


class DcbmEngineTests(unittest.TestCase):
    def test_merchant_classification_patterns(self):
        self.assertEqual("SmartBuy Flights", dcbm_engine.classify_merchant("EMT FLIGHT VIA SMARTBU").name)
        self.assertEqual("SmartBuy Flights", dcbm_engine.classify_merchant("YATRA FLIGHT VIA SMART").name)
        self.assertEqual("SmartBuy Flights", dcbm_engine.classify_merchant("GOIBIBO FLIGHT VIA SMA").name)
        self.assertEqual("SmartBuy Hotels", dcbm_engine.classify_merchant("TAJ HOTEL VIA SMARTBUY").name)
        self.assertEqual("SmartBuy Instant Vouchers", dcbm_engine.classify_merchant("GYFTR VOUCHER PURCHASE").name)
        self.assertEqual("Jewellery", dcbm_engine.classify_merchant("SRI GANESH DIAMONDS AN").name)
        self.assertEqual("Airport Lounge", dcbm_engine.classify_merchant("WWW LOUNGEONE AI").name)
        self.assertEqual("General Retail", dcbm_engine.classify_merchant("AMAZON INDIA").name)

    def test_points_calculation_flooring(self):
        flight = dcbm_engine.CATEGORIES["smartbuy_flight"]
        # 149 INR -> 0 blocks
        blocks, base, acc = dcbm_engine.calculate_points_for_amount(149.0, flight)
        self.assertEqual(0, blocks)
        self.assertEqual(0, base)
        self.assertEqual(0, acc)

        # 299 INR -> 1 block of 150
        blocks, base, acc = dcbm_engine.calculate_points_for_amount(299.0, flight)
        self.assertEqual(1, blocks)
        self.assertEqual(5, base)
        self.assertEqual(20, acc)

        # 19,436 INR -> 129 blocks
        blocks, base, acc = dcbm_engine.calculate_points_for_amount(19436.0, flight)
        self.assertEqual(129, blocks)
        self.assertEqual(645, base)
        self.assertEqual(2580, acc)

    def test_billing_cycle_dates(self):
        # Before 13th
        start, end = dcbm_engine.get_billing_cycle(date(2026, 9, 10), cycle_end_day=13)
        self.assertEqual(date(2026, 8, 14), start)
        self.assertEqual(date(2026, 9, 13), end)

        # After 13th
        start, end = dcbm_engine.get_billing_cycle(date(2026, 9, 15), cycle_end_day=13)
        self.assertEqual(date(2026, 9, 14), start)
        self.assertEqual(date(2026, 10, 13), end)

    def test_calendar_quarter_dates(self):
        q, label, start, end = dcbm_engine.get_calendar_quarter(date(2026, 9, 10))
        self.assertEqual(3, q)
        self.assertEqual("Q3 2026", label)
        self.assertEqual(date(2026, 7, 1), start)
        self.assertEqual(date(2026, 9, 30), end)

    def test_daily_and_monthly_cap_clamping(self):
        # 1 transaction with raw 2,580 accelerated RP should clamp to 2,500 daily
        txs = [{
            "message_id": "test1",
            "tx_date": date(2026, 8, 29),
            "is_smartbuy": True,
            "raw_accelerated_points": 2580,
        }]
        headroom = dcbm_engine.compute_cap_headroom(
            txs,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            as_of=date(2026, 8, 30),
            monthly_cap=10000,
            daily_cap=2500,
        )
        self.assertEqual(2500, headroom["earned"])
        self.assertEqual(7500, headroom["remaining"])
        self.assertEqual(25.0, headroom["percent_used"])

    def test_complete_dashboard_data_loading(self):
        data = dcbm_engine.compute_all_dashboard_data(CARD_DIR, as_of=date(2026, 9, 10))
        self.assertEqual("HDFC Diners Black Metal Credit Card", data["card_name"])
        self.assertEqual("2360", data["card_ending"])

        # Current calendar month (September 2026) has 1 SmartBuy flight (11 Sept: 1,140 RP)
        sept_cap = data["caps"]["calendar_month"]
        self.assertEqual(1140, sept_cap["earned"])
        self.assertEqual(8860, sept_cap["remaining"])
        self.assertEqual("ACTIVE HEADROOM", sept_cap["status_label"])

        # Current billing cycle (14 Aug - 13 Sep) contains the 2 August + 1 September SmartBuy flights
        cycle_cap = data["caps"]["billing_cycle"]
        self.assertEqual(4880, cycle_cap["earned"])
        self.assertEqual(5120, cycle_cap["remaining"])

        # Welcome milestone is 100% met
        welcome = data["milestones"]["welcome"]
        self.assertTrue(welcome["met"])
        self.assertEqual(100.0, welcome["progress"])

    def test_spend_simulator_projection(self):
        data = dcbm_engine.compute_all_dashboard_data(CARD_DIR, as_of=date(2026, 9, 10))
        sim = dcbm_engine.simulate_spend(data, spend_amount=15000.0, category_key="smartbuy_flight")

        # 15,000 INR on flight -> 100 blocks of 150 -> 500 base RP, 2,000 accelerated RP
        self.assertEqual(500, sim["base_points"])
        self.assertEqual(2000, sim["accelerated_points"])
        self.assertEqual(2500, sim["total_points"])
        self.assertFalse(sim["is_capped"])
        self.assertEqual(2500.0, sim["value_smartbuy"])
        self.assertEqual(16.67, sim["effective_reward_rate"])


    def test_monthly_history_breakdown(self):
        data = dcbm_engine.compute_all_dashboard_data(CARD_DIR, as_of=date(2026, 9, 12))
        history = data["monthly_history"]
        self.assertGreaterEqual(len(history), 3)

        # August 2026 verification
        aug = next(h for h in history if h["year"] == 2026 and h["month"] == 8)
        self.assertEqual(3060, aug["base_points"])
        self.assertEqual(3740, aug["accelerated_points"])
        self.assertEqual(6800, aug["total_points"])
        self.assertEqual(37.4, aug["accelerated_percent_used"])
        self.assertEqual(6260, aug["accelerated_remaining"])
        self.assertEqual(92206.59, aug["total_spend"])


    def test_redemptions_tracking(self):
        data = dcbm_engine.compute_all_dashboard_data(CARD_DIR, as_of=date(2026, 9, 12))
        pts = data["points_summary"]
        self.assertIn("net_available", pts)
        self.assertIn("total_redeemed", pts)
        self.assertEqual(pts["net_available"], pts["total_estimated"] - pts["total_redeemed"])
        self.assertGreaterEqual(pts["total_redeemed"], 14007)
        self.assertIn("redemptions", data)
        self.assertGreaterEqual(len(data["redemptions"]), 1)


if __name__ == "__main__":
    unittest.main()

