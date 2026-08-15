from pathlib import Path


REPORT = Path(__file__).resolve().parent / "cashback_cap_report.md"


def test_active_waiver_and_cashback_caps_show_days_left():
    report = REPORT.read_text()

    assert "### Current Waiver Year" in report
    assert "### Flipkart Cashback Cap" in report
    assert "### Myntra Cashback Cap" in report
    assert "### Cleartrip Cashback Cap" in report
    days_lines = [line for line in report.splitlines() if line.startswith("- Days left:")]
    assert len(days_lines) >= 4
    assert all(line != "- Days left: Pending" for line in days_lines)
