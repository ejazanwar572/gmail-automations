import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
SPEC = importlib.util.spec_from_file_location("hdfc_sync_alerts", ROOT / "sync_alerts.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


def encoded(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


TRANSACTION_SUBJECT = "HDFC Bank Credit Card transaction alert"


def message(message_id, body, *, subject=TRANSACTION_SUBJECT):
    return {
        "id": message_id,
        "internalDate": "1783267200000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Sun, 05 Jul 2026 12:00:00 +0530"},
            ],
            "body": {"data": encoded(body)},
        },
    }


class FakeRequest:
    def __init__(self, value): self.value = value
    def execute(self): return self.value


class FakeMessages:
    def __init__(self, pages, messages):
        self.pages, self.messages = pages, messages
        self.tokens, self.queries = [], []

    def list(self, **kwargs):
        token = kwargs.get("pageToken")
        self.tokens.append(token)
        self.queries.append(kwargs["q"])
        return FakeRequest(self.pages[token])

    def get(self, **kwargs):
        return FakeRequest(self.messages[kwargs["id"]])


class FakeService:
    def __init__(self, api): self.api = api
    def users(self): return self
    def messages(self): return self.api


class SyncAlertsTests(unittest.TestCase):
    def test_parses_production_debit_shape_and_uses_exact_narrow_query(self):
        body = (FIXTURES / "production-purchase-alert-sanitized.txt").read_text()
        self.assertTrue(sync.is_hard_filtered_candidate(body))
        self.assertEqual(
            {"date": "2026-07-15", "merchant": "TEST MERCHANT", "amount": 1234.56},
            sync.parse_transaction(body),
        )
        self.assertEqual(
            'from:alerts@hdfcbank.bank.in subject:"A payment was made using your Credit Card" "ending 2360" -in:trash -in:spam',
            sync.QUERY,
        )

    def test_production_filter_excludes_declines_refunds_and_statements(self):
        body = (FIXTURES / "production-purchase-alert-sanitized.txt").read_text()
        for replacement in (
            "Your transaction was declined for Credit Card ending 2360",
            body.replace("has been debited", "has been refunded"),
            "Your HDFC Bank Credit Card ending 2360 statement is ready",
        ):
            self.assertFalse(sync.is_hard_filtered_candidate(replacement))

    def test_parser_accepts_only_purchase_for_card_2360(self):
        text = "Rs. 88,800.00 spent on HDFC Bank Credit Card ending 2360 at KAULESH CHANDRA on 05-07-2026."
        self.assertEqual(
            {"date": "2026-07-05", "merchant": "KAULESH CHANDRA", "amount": 88800.0},
            sync.parse_transaction(text),
        )
        with self.assertRaises(sync.SyncError):
            sync.parse_transaction(text.replace("2360", "1234"))

    def test_statement_subject_is_not_a_transaction(self):
        self.assertFalse(sync.is_transaction_subject("Your HDFC Bank statement is ready"))
        self.assertTrue(sync.is_transaction_subject(TRANSACTION_SUBJECT))
        self.assertTrue(sync.is_transaction_subject("A payment was made using your Credit Card"))

    def test_alternate_purchase_subject_is_accepted_from_hard_filtered_body(self):
        body = "INR 1,234.50 spent on HDFC Bank Credit Card ending 2360 at CORNER STORE on 06-07-2026."
        api = FakeMessages(
            {None: {"messages": [{"id": "alt"}]}},
            {"alt": message("alt", body, subject="Alert: You have spent using your HDFC Bank Card")},
        )
        with tempfile.TemporaryDirectory() as td:
            result = sync.sync(FakeService(api), Path(td), run_id="alternate")
        self.assertEqual(1, result["parsed_count"])
        self.assertEqual(["alt"], result["message_ids_seen"])

    def test_negative_helper_classification_rejects_unrelated_mail(self):
        body = "Your HDFC Diners Black Metal Credit Card ending 2360 statement is ready."
        self.assertFalse(sync.is_hard_filtered_candidate(body))

    def test_mixed_valid_and_template_drift_preserves_exact_prior_files(self):
        valid = (FIXTURES / "production-purchase-alert-sanitized.txt").read_text()
        drift = "A payment was made on your HDFC Bank Credit Card ending 2360, but this template changed."
        api = FakeMessages(
            {None: {"messages": [{"id": "valid"}, {"id": "drift"}]}},
            {"valid": message("valid", valid, subject="A payment was made using your Credit Card"),
             "drift": message("drift", drift, subject="A payment was made using your Credit Card")},
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); alerts = root / "gmail_alerts.json"; metadata = root / "sync_metadata.json"
            old_alerts, old_metadata = b'[{"message_id":"old"}]\n', b'{"run_id":"old"}\n'
            alerts.write_bytes(old_alerts); metadata.write_bytes(old_metadata)
            with self.assertRaises(sync.SyncError):
                sync.sync(FakeService(api), root)
            self.assertEqual(old_alerts, alerts.read_bytes())
            self.assertEqual(old_metadata, metadata.read_bytes())

    def test_paginated_sync_deduplicates_ids_and_records_provenance(self):
        body = "Rs. 88,800.00 spent on HDFC Bank Credit Card ending 2360 at KAULESH CHANDRA on 05-07-2026."
        api = FakeMessages(
            {None: {"messages": [{"id": "b"}], "nextPageToken": "p2"},
             "p2": {"messages": [{"id": "a"}, {"id": "b"}]}},
            {"a": message("a", body), "b": message("b", body)},
        )
        with tempfile.TemporaryDirectory() as td:
            run_id = "hdfc-run"
            metadata = sync.sync(FakeService(api), Path(td), run_id=run_id)
            alerts = json.loads((Path(td) / "gmail_alerts.json").read_text())
        self.assertEqual(api.tokens, [None, "p2"])
        self.assertEqual([item["message_id"] for item in alerts], ["a", "b"])
        self.assertEqual("gmail-api", metadata["source"])
        self.assertEqual("2360", metadata["card_ending"])
        self.assertEqual(run_id, metadata["run_id"])
        self.assertEqual(len(alerts), metadata["parsed_count"])
        self.assertEqual(["a", "b"], metadata["message_ids_seen"])
        self.assertEqual(1, metadata["skipped_duplicate_count"])

    def test_failed_metadata_replace_restores_prior_exact_bytes(self):
        body = "Rs. 88,800.00 spent on HDFC Bank Credit Card ending 2360 at KAULESH CHANDRA on 05-07-2026."
        api = FakeMessages({None: {"messages": [{"id": "a"}]}}, {"a": message("a", body)})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            alerts, metadata = root / "gmail_alerts.json", root / "sync_metadata.json"
            old_alerts, old_metadata = b'[{"old":true}]\n', b'{"old":true}\n'
            alerts.write_bytes(old_alerts); metadata.write_bytes(old_metadata)
            real_replace, calls = sync.os.replace, []

            def fail_second(source, target):
                calls.append(Path(target).name)
                if len(calls) == 2:
                    raise OSError("metadata replace failed")
                real_replace(source, target)

            with patch.object(sync.os, "replace", side_effect=fail_second):
                with self.assertRaises(sync.SyncError):
                    sync.sync(FakeService(api), root)
            self.assertEqual(old_alerts, alerts.read_bytes())
            self.assertEqual(old_metadata, metadata.read_bytes())

    def test_fully_filtered_result_preserves_prior_nonempty_cache(self):
        api = FakeMessages(
            {None: {"messages": [{"id": "statement"}]}},
            {"statement": message("statement", "Your account statement is ready.",
                                  subject="Your HDFC Bank statement is ready")},
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            alerts, metadata = root / "gmail_alerts.json", root / "sync_metadata.json"
            old_alerts, old_metadata = b'[{"message_id":"old"}]\n', b'{"run_id":"old"}\n'
            alerts.write_bytes(old_alerts); metadata.write_bytes(old_metadata)
            with self.assertRaises(sync.SyncError):
                sync.sync(FakeService(api), root)
            self.assertEqual(old_alerts, alerts.read_bytes())
            self.assertEqual(old_metadata, metadata.read_bytes())

    def test_first_replace_failure_preserves_files_and_cleans_temps(self):
        body = "Rs. 10.00 spent on HDFC Bank Credit Card ending 2360 at SHOP on 05-07-2026."
        api = FakeMessages({None: {"messages": [{"id": "a"}]}}, {"a": message("a", body)})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); alerts = root / "gmail_alerts.json"; metadata = root / "sync_metadata.json"
            old_alerts, old_metadata = b"old alerts", b"old metadata"
            alerts.write_bytes(old_alerts); metadata.write_bytes(old_metadata)
            with patch.object(sync.os, "replace", side_effect=OSError("first replace failed")):
                with self.assertRaises(sync.SyncError):
                    sync.sync(FakeService(api), root)
            self.assertEqual(old_alerts, alerts.read_bytes())
            self.assertEqual(old_metadata, metadata.read_bytes())
            self.assertEqual([], list(root.glob(".*.tmp")))

    def test_second_replace_failure_without_prior_files_leaves_no_files(self):
        body = "Rs. 10.00 spent on HDFC Bank Credit Card ending 2360 at SHOP on 05-07-2026."
        api = FakeMessages({None: {"messages": [{"id": "a"}]}}, {"a": message("a", body)})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); real_replace = sync.os.replace; calls = []
            def fail_second(source, target):
                calls.append(Path(target).name)
                if len(calls) == 2: raise OSError("metadata replace failed")
                real_replace(source, target)
            with patch.object(sync.os, "replace", side_effect=fail_second):
                with self.assertRaises(sync.SyncError):
                    sync.sync(FakeService(api), root)
            self.assertFalse((root / "gmail_alerts.json").exists())
            self.assertFalse((root / "sync_metadata.json").exists())
            self.assertEqual([], list(root.glob(".*.tmp")))

    def test_failed_restore_cleans_restore_temp(self):
        body = "Rs. 10.00 spent on HDFC Bank Credit Card ending 2360 at SHOP on 05-07-2026."
        api = FakeMessages({None: {"messages": [{"id": "a"}]}}, {"a": message("a", body)})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); alerts = root / "gmail_alerts.json"; metadata = root / "sync_metadata.json"
            old_alerts, old_metadata = b"old alerts", b"old metadata"
            alerts.write_bytes(old_alerts); metadata.write_bytes(old_metadata)
            real_replace, calls = sync.os.replace, []
            def fail_metadata_and_restore(source, target):
                calls.append(Path(target).name)
                if len(calls) >= 2: raise OSError("replace failed")
                real_replace(source, target)
            with patch.object(sync.os, "replace", side_effect=fail_metadata_and_restore):
                with self.assertRaises(sync.SyncError):
                    sync.sync(FakeService(api), root)
            self.assertEqual(old_alerts, alerts.read_bytes())
            self.assertEqual(old_metadata, metadata.read_bytes())
            self.assertEqual([], list(root.glob(".*.tmp")))

    def test_unrecoverable_restore_raises_distinct_preservation_error(self):
        body = "Rs. 10.00 spent on HDFC Bank Credit Card ending 2360 at SHOP on 05-07-2026."
        api = FakeMessages({None: {"messages": [{"id": "a"}]}}, {"a": message("a", body)})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "gmail_alerts.json").write_bytes(b"old alerts")
            (root / "sync_metadata.json").write_bytes(b"old metadata")
            real_replace, calls = sync.os.replace, []
            def fail_metadata_and_restore(source, target):
                calls.append(Path(target).name)
                if len(calls) >= 2: raise OSError("replace failed")
                real_replace(source, target)
            with patch.object(sync.os, "replace", side_effect=fail_metadata_and_restore), \
                 patch.object(sync, "_rewrite_exact", side_effect=OSError("direct restore failed")):
                with self.assertRaisesRegex(sync.SyncError, "preserv|recover|corrupt"):
                    sync.sync(FakeService(api), root)
            self.assertEqual([], list(root.glob(".*.tmp")))


if __name__ == "__main__":
    unittest.main()
