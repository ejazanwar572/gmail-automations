import unittest
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import phonepe_tracker


class PhonePeStatementCycleTests(unittest.TestCase):
    def test_cycle_uses_statement_confirmed_23rd_close(self):
        self.assertEqual(
            (date(2026, 7, 24), date(2026, 8, 23)),
            phonepe_tracker._cycle(date(2026, 8, 2)),
        )

    def test_summary_exposes_confirmed_statement_cycle_evidence(self):
        summary = phonepe_tracker.build_summary(
            [],
            {},
            as_of=date(2026, 8, 2),
            run_id="run-1",
            generated_at="2026-08-02T12:00:00+05:30",
        )

        self.assertEqual("2026-07-24", summary["cycle"]["start"])
        self.assertEqual("2026-08-23", summary["cycle"]["end"])
        self.assertEqual("confirmed", summary["cycle"]["evidence_status"])
        self.assertEqual("2026-07-23", summary["cycle"]["statement_date"])


if __name__ == "__main__":
    unittest.main()
