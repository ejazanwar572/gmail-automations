import json
from datetime import datetime as RealDateTime

import update_report


class FixedDateTime(RealDateTime):
    @classmethod
    def now(cls):
        return cls(2026, 6, 28, 9, 0, 0)


def test_report_uses_active_cycle_and_includes_current_alert(tmp_path, monkeypatch):
    alerts_path = tmp_path / "gmail_alerts.json"
    statements_path = tmp_path / "statements_data.json"
    report_path = tmp_path / "cashback_cap_report.md"

    alerts_path.write_text(json.dumps([
        {
            "subject": "INR 3739 spent on credit card no. XX6969 at FLIPKART IN",
            "date": "28/06/2026",
            "amount": 3739.0,
        },
        {
            "subject": "INR 15405 spent on credit card no. XX6969 at PAY*WWW MYN",
            "date": "17/06/2026",
            "amount": 15405.0,
        },
    ]))
    statements_path.write_text(json.dumps({"statements": [], "summary": [{"month": "May 2026"}]}))

    monkeypatch.setattr(update_report, "ALERTS_FILE", str(alerts_path))
    monkeypatch.setattr(update_report, "STATEMENTS_FILE", str(statements_path))
    monkeypatch.setattr(update_report, "REPORT_PATH", str(report_path))
    monkeypatch.setattr(update_report, "PDF_DIR", str(tmp_path))
    monkeypatch.setattr(update_report, "datetime", FixedDateTime)

    update_report.update_report()

    report = report_path.read_text()
    assert "Current Statement Period (Ongoing):** June 16, 2026 – July 15, 2026" in report
    assert "Current Axis Statement Quarter:** June 16, 2026 – September 15, 2026 (Statement Quarter 2)" in report
    assert "| Bucket | Cashback Rate | Statement-Quarter Cap | Achieved So Far | Left | Spend Needed to Fill |" in report
    assert "| Flipkart | 5% | ₹4,000.00 | ₹186.00 (4.7%) | ₹3,814.00 | ₹76,280.00 |" in report
    assert "| Myntra | 7.5% | ₹4,000.00 | ₹1,155.00 (28.9%) | ₹2,845.00 | ₹37,933.33 |" in report
    assert "| **Total** | Mixed | **₹12,000.00** | **₹1,341.00 (11.2%)** | **₹10,659.00** | Category-specific |" in report
    assert "This report aggregates your Flipkart Axis Bank Credit Card spends" not in report
    assert "Max Statement-Quarter Cap" in report
    assert "Remaining Statement-Quarter Cap Room" in report
    assert "Max Q3 Cap" not in report
    assert "Remaining Q3 Cap Room" not in report
    assert "Cashback Credited & Verified? | Quarter Cashback Total |" in report
    assert "| **January 2026** | ₹195.00 | ₹865.00 | ₹0.00 | **₹1,060.00** | N/A | **₹2,689.00** |" in report
    assert "| **February 2026** | ₹439.00 | ₹120.00 | ₹0.00 | **₹559.00** | N/A | **₹2,689.00** |" in report
    assert "| **March 2026** | ₹1,007.00 | ₹63.00 | ₹0.00 | **₹1,070.00** | N/A | **₹2,689.00** |" in report
    assert "| **April 2026** | ₹195.00 | ₹165.00 | ₹0.00 | **₹360.00** | N/A | **₹3,842.00** |" in report
    assert "| **May 2026** | ₹186.00 | ₹11.00 | ₹3,285.00 | **₹3,482.00** | N/A | **₹3,842.00** |" in report
    assert "| **June 2026 *(Est.)*** | ₹0.00 | ₹0.00 | ₹0.00 | ***₹0.00 (Est.)*** | N/A | **₹3,842.00** |" in report
    assert "| **July 2026 *(Ongoing)*** | ₹186.00 (4.7%) | ₹1,155.00 (28.9%) | ₹0.00 (0.0%) | ***₹1,341.00 (Est.)*** | *Pending (Next Statement)* | **₹1,341.00** |" in report
    assert "Jun 28 | Flipkart | ₹3,739 | Flipkart" in report
    assert "Jun 17 | Myntra | ₹15,405 | Myntra" in report
    assert "### Current Waiver Year" in report
    assert "### Flipkart Cashback Cap" in report
    assert "### Myntra Cashback Cap" in report
    assert "### Cleartrip Cashback Cap" in report
    bars = [line for line in report.splitlines() if line.startswith("`") and line.endswith("%`")]
    assert len(bars) >= 4
    assert all(len(line.split(" ", 1)[0].strip("`")) == 20 for line in bars)
