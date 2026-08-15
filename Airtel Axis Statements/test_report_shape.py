from pathlib import Path


REPORT = Path(__file__).resolve().parent / "cashback_cap_report.md"


def test_executive_summary_uses_cap_room_grid():
    report = REPORT.read_text()

    assert "| Bucket | Cashback Rate | Statement-Cycle Cap | Achieved So Far | Left | Spend Needed to Fill |" in report
    assert "| 25% Airtel | 25% | ₹250.00 |" in report
    assert "| 10% Utilities | 10% | ₹250.00 |" in report
    assert "| 10% Merchants | 10% | ₹500.00 |" in report
    assert "| **Total** | Mixed | **₹1,000.00** |" in report
    assert "This report combines your historical cashback cap achievement" not in report


def test_active_waiver_and_cashback_caps_use_progress_bars():
    report = REPORT.read_text()
    assert "### Current Waiver Year" in report
    assert "### 25% Airtel Cashback Cap" in report
    assert "### 10% Utilities Cashback Cap" in report
    assert "### 10% Merchants Cashback Cap" in report
    bars = [line for line in report.splitlines() if line.startswith("`") and line.endswith("%`")]
    assert len(bars) >= 4
    assert all(len(line.split(" ", 1)[0].strip("`")) == 20 for line in bars)
    days_lines = [line for line in report.splitlines() if line.startswith("- Days left:")]
    assert len(days_lines) >= 4
    assert all(line != "- Days left: Pending" for line in days_lines)
