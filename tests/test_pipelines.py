from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "HDFC Diners Black Metal Statements"))
sys.path.insert(0, str(ROOT / "HSBC Live Plus Statements"))

import dcbm_engine
import hsbc_engine


class PipelineIntegrationTests(unittest.TestCase):
    def test_hdfc_pipeline_in_process_execution(self):
        hdfc_dir = ROOT / "HDFC Diners Black Metal Statements"
        res = dcbm_engine.run_card_pipeline(hdfc_dir, sync_source="none", download_statements_pdf=False)
        self.assertTrue(res.get("ok"), f"HDFC pipeline failed: {res}")
        self.assertIn("validate", res.get("steps", {}))
        self.assertIn("update_report", res.get("steps", {}))

    def test_hsbc_pipeline_in_process_execution(self):
        hsbc_dir = ROOT / "HSBC Live Plus Statements"
        res = hsbc_engine.run_card_pipeline(hsbc_dir, sync_source="none")
        self.assertTrue(res.get("ok"), f"HSBC pipeline failed: {res}")
        self.assertIn("parse_statements", res.get("steps", {}))
        self.assertIn("validate", res.get("steps", {}))
        self.assertIn("update_report", res.get("steps", {}))


if __name__ == "__main__":
    unittest.main()
