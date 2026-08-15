from pathlib import Path


REPORT = Path(__file__).resolve().parents[1] / "cashback_cap_report.md"


def test_current_cycle_status_includes_max_cap_total():
    report = REPORT.read_text()

    assert "**Current Statement Period (Ongoing):** June 24, 2026 – July 23, 2026" in report
    assert "**Statement Cycle:** June 24, 2026 - July 23, 2026" in report
    assert "**5% online reset date:** July 24, 2026" in report
    assert "May 24, 2026 – June 23, 2026" not in report
    assert "| Bucket | Cashback Rate | Statement-Cycle Cap | Achieved So Far | Left | Spend Needed to Fill |" in report
    assert "Do not use this card for online spends expecting 5% cashback right now" not in report
    assert "| Category | Tracked Transactions | Max Cap | Total Spend | Cashback Earned | Remaining Cap Room | Status |" in report


def test_historical_statement_cap_status_uses_icons():
    report = REPORT.read_text()

    assert "| **August 2025** |" in report
    assert "| ✅ Capped |" in report
    assert "| Not capped |" in report
    assert "| 🔄 In progress |" not in report
    assert "August 23, 2024 - August 22, 2025" in report
    assert "| August 23, 2024 - August 22, 2025 | posted statements | **₹4,212.90** | ₹200,000.00 | 2.1% | ₹195,787.10 left | Not met - fee charged |" in report
    assert "[CAPPED]" not in report


def test_active_waiver_and_cashback_caps_use_progress_bars():
    report = REPORT.read_text()
    assert "### Current Waiver Year" in report
    assert "### 5% Online Cashback Cap" in report
    assert "### 1% Offline Cashback Cap" in report
    bars = [line for line in report.splitlines() if line.startswith("`") and line.endswith("%`")]
    assert len(bars) >= 3
    assert all(len(line.split(" ", 1)[0].strip("`")) == 20 for line in bars)
    days_lines = [line for line in report.splitlines() if line.startswith("- Days left:")]
    assert len(days_lines) >= 3
    assert all(line != "- Days left: Pending" for line in days_lines)
