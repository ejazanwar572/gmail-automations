#!/usr/bin/env python3
"""
Unit tests for Amazon Price Tracker.
Verifies data modeling, HTML parsing, price calculations, and SQLite persistence.
"""

import os
import json
import sqlite3
import tempfile
import unittest
from amazon_price_tracker import (
    init_db,
    sync_products_from_config,
    parse_price_str,
    extract_product_details_from_html,
    get_product_price_summary,
    generate_markdown_report
)

class TestAmazonPriceTracker(unittest.TestCase):

    def setUp(self):
        # Create isolated temporary database and config (Lesson L-004)
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.test_dir.name, "test_amazon_prices.db")
        self.config_path = os.path.join(self.test_dir.name, "test_products.json")
        self.report_path = os.path.join(self.test_dir.name, "test_report.md")

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        init_db(self.conn)

        # Sample test products
        self.sample_products = [
            {
                "asin": "B0GPRPQF23",
                "title": "Godrej Fab Liquid Detergent 5L",
                "category": "Cleaning & Household",
                "baseline_price": 525.0,
                "target_price": 499.0,
                "active": True
            },
            {
                "asin": "B00E3AP5KS",
                "title": "Horlicks Chocolate 1kg",
                "category": "Groceries & Food",
                "baseline_price": 361.0,
                "target_price": 330.0,
                "active": True
            }
        ]
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.sample_products, f)

    def tearDown(self):
        self.conn.close()
        self.test_dir.cleanup()

    def test_price_string_parser(self):
        self.assertEqual(parse_price_str("₹525.00"), 525.0)
        self.assertEqual(parse_price_str("₹1,249.50"), 1249.5)
        self.assertEqual(parse_price_str("  361  "), 361.0)
        self.assertIsNone(parse_price_str(""))
        self.assertIsNone(parse_price_str("N/A"))

    def test_html_detail_extraction(self):
        mock_html = """
        <html>
            <span id="productTitle">Godrej Fab Liquid Detergent Refill Pouch 5L</span>
            <div id="corePriceDisplay_desktop_feature_div">
                <span class="a-price aok-align-center reinventPricePriceToPayMargin priceToPay">
                    <span class="a-offscreen">₹499.00</span>
                </span>
                <span class="a-price a-text-price">
                    <span class="a-offscreen">₹600.00</span>
                </span>
            </div>
            <div id="availability">
                <span class="a-size-medium a-color-success">In stock</span>
            </div>
            <span class="deal-badge">Limited time deal</span>
        </html>
        """
        details = extract_product_details_from_html(mock_html)
        self.assertEqual(details["price"], 499.0)
        self.assertEqual(details["mrp"], 600.0)
        self.assertTrue(details["in_stock"])
        self.assertIn("Godrej Fab", details["title"])
        self.assertEqual(details["deal_badge"], "Limited Time Deal")

    def test_product_sync_and_sqlite_persistence(self):
        synced = sync_products_from_config(self.conn, self.config_path)
        self.assertEqual(len(synced), 2)

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM products WHERE asin = 'B0GPRPQF23'")
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["baseline_price"], 525.0)
        self.assertEqual(row["target_price"], 499.0)

    def test_price_drop_summary_and_all_time_low(self):
        sync_products_from_config(self.conn, self.config_path)
        cursor = self.conn.cursor()

        # Insert historical checks
        # Check 1: 520 (Initial)
        cursor.execute("""
            INSERT INTO price_history (asin, timestamp, price, mrp, in_stock, deal_badge, raw_price_str)
            VALUES ('B0GPRPQF23', '2026-08-01T10:00:00', 520.0, 600.0, 1, NULL, '₹520.00')
        """)
        # Check 2: 480 (Price drop & target hit)
        cursor.execute("""
            INSERT INTO price_history (asin, timestamp, price, mrp, in_stock, deal_badge, raw_price_str)
            VALUES ('B0GPRPQF23', '2026-08-19T10:00:00', 480.0, 600.0, 1, 'Limited Time Deal', '₹480.00')
        """)
        self.conn.commit()

        summary = get_product_price_summary(self.conn, 'B0GPRPQF23')
        self.assertIsNotNone(summary)
        self.assertEqual(summary["latest_price"], 480.0)
        self.assertEqual(summary["prev_price"], 520.0)
        self.assertEqual(summary["drop_from_baseline"], 45.0) # 525 - 480
        self.assertEqual(summary["drop_from_prev"], 40.0) # 520 - 480
        self.assertTrue(summary["is_all_time_low"])
        self.assertTrue(summary["hit_target"]) # 480 <= 499

    def test_markdown_report_generation(self):
        sync_products_from_config(self.conn, self.config_path)
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO price_history (asin, timestamp, price, mrp, in_stock, deal_badge, raw_price_str)
            VALUES ('B0GPRPQF23', '2026-08-19T10:00:00', 480.0, 600.0, 1, 'Limited Time Deal', '₹480.00')
        """)
        self.conn.commit()

        report_file = generate_markdown_report(self.conn, output_path=self.report_path)
        self.assertTrue(os.path.exists(report_file))

        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Amazon India Price Tracker Report", content)
        self.assertIn("Target Price Alerts", content)
        self.assertIn("Active Price Drops", content)
        self.assertIn("Godrej Fab", content)

if __name__ == "__main__":
    unittest.main()
