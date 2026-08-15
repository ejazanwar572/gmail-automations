import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


WORKFLOW_PATH = Path(__file__).resolve().parents[1] / "run_workflow.py"


def load_workflow():
    spec = importlib.util.spec_from_file_location("hdfc_run_workflow", WORKFLOW_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunWorkflowTests(unittest.TestCase):
    def test_sync_source_routes_expected_script_sequence(self):
        expected = {
            None: ["sync_alerts.py", "parse_statements.py", "validate_statements.py", "update_report.py"],
            "gmail-api": ["sync_alerts.py", "parse_statements.py", "validate_statements.py", "update_report.py"],
            "mcp-step-logs": ["sync_gmail_mcp.py", "parse_statements.py", "validate_statements.py", "update_report.py"],
            "none": ["parse_statements.py", "validate_statements.py", "update_report.py"],
        }

        for sync_source, expected_scripts in expected.items():
            with self.subTest(sync_source=sync_source):
                workflow = load_workflow()
                argv = [str(WORKFLOW_PATH)]
                if sync_source is not None:
                    argv += ["--sync-source", sync_source]
                with patch.object(sys, "argv", argv), patch.object(workflow.subprocess, "run") as run:
                    run.return_value.returncode = 0
                    self.assertEqual(workflow.main(), 0)

                actual_scripts = [Path(call.args[0][1]).name for call in run.call_args_list]
                self.assertEqual(actual_scripts, expected_scripts)

    def test_nonzero_step_stops_later_scripts_and_returns_code(self):
        workflow = load_workflow()
        results = [unittest.mock.Mock(returncode=0), unittest.mock.Mock(returncode=7)]
        with patch.object(sys, "argv", [str(WORKFLOW_PATH), "--sync-source", "none"]), patch.object(
            workflow.subprocess, "run", side_effect=results
        ) as run:
            self.assertEqual(workflow.main(), 7)

        actual_scripts = [Path(call.args[0][1]).name for call in run.call_args_list]
        self.assertEqual(actual_scripts, ["parse_statements.py", "validate_statements.py"])


if __name__ == "__main__":
    unittest.main()
