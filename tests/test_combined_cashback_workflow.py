import importlib.util
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


TARGET_BASE = Path("/Users/ejazanwar/Documents/Gmail Automations")


def load_target_module(name, filename):
    path = TARGET_BASE / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def aggregate_report_text(extra=""):
    return f"""
    # Monthly Aggregate Spend & Cashback Report

    ## 1. 2026 Monthly Aggregate Summary

    | Month | Airtel Axis Spend | Airtel Axis Cashback | Flipkart Axis Spend | Flipkart Axis Cashback | SBI Cashback Spend | SBI Cashback Earned | Total Spends | Total Cashback Earned | Effective Cashback Rate |
    | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
    | January 2026 | ₹10k | ₹100 | ₹20k | ₹200 | ₹30k | ₹300 | **₹60k** | **₹600** | **1.00%** |

    ## 2. Card-wise Contribution (YTD 2026)

    | Metric | Airtel Axis | Flipkart Axis | SBI Cashback | Total |
    | :--- | :---: | :---: | :---: | :---: |
    | **Cumulative Spends** | ₹10k | ₹20k | ₹30k | **₹60k** |
    | **Cumulative Cashback** | ₹100 | ₹200 | ₹300 | **₹600** |
    | **Share of Total Spends** | 16.7% | 33.3% | 50.0% | **100.0%** |
    | **Share of Total Cashback** | 16.7% | 33.3% | 50.0% | **100.0%** |
    | **Effective Rate** | **1.00%** | **1.00%** | **1.00%** | **1.00%** |

    ## 3. Key Observations & Optimization Strategies
    Cashback room remains available where caps are not reached.
    {extra}
    """


def card_report_text(title, total_cap):
    return f"""
    # {title}

    ## 1. Executive Summary
    Summary.

    ## 2. Historical & Ongoing Cap Achievement Summary (2026)
    | Statement Month | Cashback | Total Cashback Earned |
    | :--- | :---: | :---: |
    | **June 2026 *(Ongoing)*** | ₹100 | **₹100** |

    ## 3. June 2026 Spends & Cap Progress (Ongoing Cycle)
    | Category (Rate) | Max Cap | Tracked Transactions | Total Spend | Cashback Earned | Remaining Cap Room | Status / Spend Action |
    | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
    | **Eligible** | **{total_cap}** | 2 transactions | **₹2,000.00** | **₹100.00** | **₹0.00** | **Active.** Tracked cashback progress. |
    | **Total** | **{total_cap}** | - | **₹2,000.00** | **₹100.00** | **₹0.00** | **Active.** Tracked cashback progress. |

    ## 4. June 2026 Transaction Details
    | Date | Category | Amount | Merchant |
    | :--- | :--- | ---: | :--- |
    | Jun 01 | Eligible | ₹1,000.00 | Test Merchant |
    """


def prepare_valid_reports(base_dir):
    write(base_dir / "aggregate_report.py", """
    GLOBAL_REPORT_PATH = "/tmp/aggregate_cashback_report.md"
    """)
    write(base_dir / "aggregate_cashback_report.md", aggregate_report_text())
    write(
        base_dir / "Airtel Axis Statements" / "cashback_cap_report.md",
        card_report_text("Airtel Axis Credit Card: Cashback Cap & Spend Progress Report", "₹1,000.00"),
    )
    write(
        base_dir / "Flipkart Axis Statements" / "cashback_cap_report.md",
        card_report_text("Flipkart Axis Credit Card: Cashback Cap & Spend Progress Report", "₹12,000.00"),
    )
    write(
        base_dir / "SBI Cashback Statements" / "cashback_cap_report.md",
        card_report_text("SBI Cashback Credit Card: Cashback Cap & Spend Progress Report", "₹4,000.00"),
    )


def make_script(path, body):
    write(path, f"""
    import pathlib
    import sys

    {body}
    """)


class VerifierTests(unittest.TestCase):
    def test_valid_reports_pass_all_checks(self):
        verify = load_target_module("verify_cashback_reports", "verify_cashback_reports.py")
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            prepare_valid_reports(base_dir)

            result = verify.verify_reports(base_dir=base_dir, scope="all")

            self.assertTrue(result.ok, result.summary())

    def test_aggregate_report_rejects_raw_html_and_template_literals(self):
        verify = load_target_module("verify_cashback_reports", "verify_cashback_reports.py")
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            prepare_valid_reports(base_dir)
            write(
                base_dir / "aggregate_cashback_report.md",
                aggregate_report_text("<br>{format_money(total)}"),
            )

            result = verify.verify_reports(base_dir=base_dir, scope="aggregate")

            self.assertFalse(result.ok)
            self.assertIn("raw HTML", result.summary())
            self.assertIn("template literal", result.summary())

    def test_card_report_requires_total_row_and_transaction_details(self):
        verify = load_target_module("verify_cashback_reports", "verify_cashback_reports.py")
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            prepare_valid_reports(base_dir)
            write(
                base_dir / "SBI Cashback Statements" / "cashback_cap_report.md",
                """
                # SBI Cashback Credit Card: Cashback Cap & Spend Progress Report

                ## 3. June 2026 Spends & Cap Progress (Ongoing Cycle)
                | Category (Rate) | Max Cap | Tracked Transactions | Total Spend | Cashback Earned | Remaining Cap Room | Status / Spend Action |
                | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
                | **5% Online** | **₹2,000.00** | 2 transactions | **₹2,000.00** | **₹100.00** | **₹0.00** | Active |
                """,
            )

            result = verify.verify_reports(base_dir=base_dir, scope="cards")

            self.assertFalse(result.ok)
            summary = result.summary()
            self.assertIn("SBI Cashback", summary)
            self.assertIn("Total row", summary)
            self.assertIn("transaction details", summary)


class WorkflowTests(unittest.TestCase):
    def test_aggregate_safe_validates_and_compiles_without_card_report_updates(self):
        workflow = load_target_module("cashback_tracker_all_cards", "cashback_tracker_all_cards.py")
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            prepare_valid_reports(base_dir)
            order_file = base_dir / "order.txt"
            for card_dir in ["Airtel Axis Statements", "Flipkart Axis Statements", "SBI Cashback Statements"]:
                make_script(
                    base_dir / card_dir / "validate_statements.py",
                    f"pathlib.Path({str(order_file)!r}).open('a').write('validate:{card_dir}\\n')",
                )
                make_script(
                    base_dir / card_dir / "update_report.py",
                    f"""
                    pathlib.Path({str(order_file)!r}).open('a').write('update:{card_dir}\\n')
                    pathlib.Path(__file__).with_name('cashback_cap_report.md').write_text('mutated by update', encoding='utf-8')
                    """,
                )
            make_script(
                base_dir / "aggregate_report.py",
                f"pathlib.Path({str(order_file)!r}).open('a').write('aggregate\\n')",
            )
            before = {
                path: path.read_text(encoding="utf-8")
                for path in [
                    base_dir / "Airtel Axis Statements" / "cashback_cap_report.md",
                    base_dir / "Flipkart Axis Statements" / "cashback_cap_report.md",
                    base_dir / "SBI Cashback Statements" / "cashback_cap_report.md",
                ]
            }

            result = workflow.run_workflow(
                mode="aggregate-safe",
                base_dir=base_dir,
                python_bin=sys.executable,
                sync_source="none",
            )

            self.assertEqual(0, result.exit_code, result.summary())
            order = order_file.read_text(encoding="utf-8")
            self.assertIn("validate:Airtel Axis Statements", order)
            self.assertIn("validate:Flipkart Axis Statements", order)
            self.assertIn("validate:SBI Cashback Statements", order)
            self.assertIn("aggregate", order)
            self.assertNotIn("update:", order)
            for path, content in before.items():
                self.assertEqual(content, path.read_text(encoding="utf-8"))

    def test_full_refresh_runs_card_updates_before_aggregate(self):
        workflow = load_target_module("cashback_tracker_all_cards", "cashback_tracker_all_cards.py")
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            prepare_valid_reports(base_dir)
            order_file = base_dir / "order.txt"
            for card_dir in ["Airtel Axis Statements", "Flipkart Axis Statements", "SBI Cashback Statements"]:
                make_script(
                    base_dir / card_dir / "validate_statements.py",
                    f"pathlib.Path({str(order_file)!r}).open('a').write('validate:{card_dir}\\n')",
                )
                make_script(
                    base_dir / card_dir / "update_report.py",
                    f"pathlib.Path({str(order_file)!r}).open('a').write('update:{card_dir}\\n')",
                )
            make_script(
                base_dir / "aggregate_report.py",
                f"pathlib.Path({str(order_file)!r}).open('a').write('aggregate\\n')",
            )

            result = workflow.run_workflow(
                mode="full-refresh",
                base_dir=base_dir,
                python_bin=sys.executable,
                sync_source="none",
            )

            self.assertEqual(0, result.exit_code, result.summary())
            order = order_file.read_text(encoding="utf-8").strip().splitlines()
            self.assertLess(order.index("update:Airtel Axis Statements"), order.index("aggregate"))
            self.assertLess(order.index("update:Flipkart Axis Statements"), order.index("aggregate"))
            self.assertLess(order.index("update:SBI Cashback Statements"), order.index("aggregate"))


if __name__ == "__main__":
    unittest.main()
