import base64
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hsbc_sync_alerts", ROOT / "sync_alerts.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)
FIXTURES = Path(__file__).parent / "fixtures"


def encoded(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


TRANSACTION_SUBJECT = "You have used your HSBC Credit Card ending with 8690 for a purchase transaction"


def message(message_id, body, *, mime="text/plain", subject=TRANSACTION_SUBJECT):
    return {
        "id": message_id,
        "internalDate": "1783961340000",
        "payload": {
            "mimeType": mime,
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Mon, 13 Jul 2026 22:19:00 +0530"},
            ],
            "body": {"data": encoded(body)},
        },
    }


class FakeRequest:
    def __init__(self, value=None, error=None):
        self.value, self.error = value, error

    def execute(self):
        if self.error:
            raise self.error
        return self.value


class FakeMessages:
    def __init__(self, pages, messages, get_error=None):
        self.pages, self.messages, self.get_error = pages, messages, get_error
        self.tokens = []
        self.queries = []

    def list(self, **kwargs):
        token = kwargs.get("pageToken")
        self.tokens.append(token)
        self.queries.append(kwargs.get("q"))
        return FakeRequest(self.pages[token])

    def get(self, **kwargs):
        if self.get_error:
            return FakeRequest(error=self.get_error)
        return FakeRequest(self.messages[kwargs["id"]])


class FakeUsers:
    def __init__(self, messages): self._messages = messages
    def messages(self): return self._messages


class FakeService:
    def __init__(self, messages): self._users = FakeUsers(messages)
    def users(self): return self._users


class SyncAlertsTests(unittest.TestCase):
    def test_parses_real_plain_fixture(self):
        text = (FIXTURES / "transaction-alert-plain.txt").read_text()
        parsed = sync.parse_transaction(text)
        self.assertEqual(parsed, {"date": "2026-07-13", "merchant": "BLINKIT", "amount": 437.00})

    def test_body_prefers_recursive_plain_text_then_html_fallback(self):
        payload = {"mimeType": "multipart/alternative", "parts": [
            {"mimeType": "text/html", "body": {"data": encoded("<p>HTML choice</p>")}},
            {"mimeType": "multipart/mixed", "parts": [
                {"mimeType": "text/plain", "body": {"data": encoded("Plain choice")}}
            ]},
        ]}
        self.assertEqual(sync.decode_message_body(payload), "Plain choice")
        html = (FIXTURES / "transaction-alert-html.txt").read_text()
        self.assertIn("used for INR 437.00", sync.decode_message_body(
            {"mimeType": "text/html", "body": {"data": encoded(html)}}))

    def test_hard_filter_rejects_other_card_and_non_transaction(self):
        valid = (FIXTURES / "transaction-alert-plain.txt").read_text()
        other = valid.replace("8690", "1234")
        non_transaction = (FIXTURES / "non-transaction-alert.txt").read_text()
        self.assertTrue(sync.is_hard_filtered_candidate(valid))
        self.assertFalse(sync.is_hard_filtered_candidate(other))
        self.assertFalse(sync.is_hard_filtered_candidate(non_transaction))

    def test_paginated_sync_dedupes_sorts_and_writes_metadata(self):
        body = (FIXTURES / "transaction-alert-plain.txt").read_text()
        msgs = {"b": message("b", body), "a": message("a", body),
                "x": message("x", body.replace("8690", "1111"), subject="HSBC service notice")}
        api = FakeMessages(
            {None: {"messages": [{"id": "b"}, {"id": "x"}], "nextPageToken": "p2"},
             "p2": {"messages": [{"id": "a"}, {"id": "b"}]}}, msgs)
        with tempfile.TemporaryDirectory() as td:
            result = sync.sync(FakeService(api), Path(td), run_id="run-1")
            alerts = json.loads((Path(td) / "gmail_alerts.json").read_text())
            metadata = json.loads((Path(td) / "sync_metadata.json").read_text())
        self.assertEqual(api.tokens, [None, "p2"])
        self.assertTrue(all("-in:spam" in query and "-in:trash" in query for query in api.queries))
        self.assertEqual([a["message_id"] for a in alerts], ["a", "b"])
        self.assertEqual(set(alerts[0]), {"date", "merchant", "amount", "subject", "message_id", "email_date", "source"})
        self.assertEqual(alerts[0]["source"], "gmail-api")
        self.assertEqual(metadata["source"], "gmail-api")
        self.assertEqual(metadata["message_ids_seen"], ["a", "b", "x"])
        self.assertEqual(metadata["matched_count"], 2)
        self.assertEqual(metadata["parsed_count"], 2)
        self.assertEqual(metadata["rejected_count"], 1)
        self.assertEqual(metadata["skipped_duplicate_count"], 1)
        self.assertEqual(metadata["cached_total"], 874.0)
        self.assertEqual(metadata["alert_count"], 2)
        self.assertEqual(metadata["unique_alert_count"], 2)
        self.assertEqual(metadata["previous_count"], 0)
        self.assertEqual(metadata["new_count"], 2)
        self.assertEqual(metadata["latest_alert_date"], "2026-07-13")
        self.assertEqual(metadata["card_name"], "HSBC Live+ Credit Card")
        self.assertEqual(metadata["card_ending"], "8690")
        self.assertEqual(metadata["warnings"], [])
        self.assertTrue(metadata["synced_at"].endswith("+00:00"))
        self.assertEqual(metadata["run_id"], "run-1")
        self.assertEqual(result["cached_total"], 874.0)

    def test_candidate_parse_failure_preserves_both_canonical_files(self):
        malformed = "We write to confirm that your Credit card no ending with 8690,has been used for INR BAD for payment to X on never."
        api = FakeMessages({None: {"messages": [{"id": "bad"}]}}, {"bad": message("bad", malformed)})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "gmail_alerts.json").write_text('[{"old": true}]')
            (root / "sync_metadata.json").write_text('{"old": true}')
            with self.assertRaises(sync.SyncError):
                sync.sync(FakeService(api), root, run_id="failed")
            self.assertEqual((root / "gmail_alerts.json").read_text(), '[{"old": true}]')
            self.assertEqual((root / "sync_metadata.json").read_text(), '{"old": true}')

    def test_exact_transaction_subject_with_changed_body_preserves_exact_canonical_bytes(self):
        changed = "Your purchase was approved, but the transaction template has changed. Card ending 8690."
        api = FakeMessages({None: {"messages": [{"id": "drift"}]}}, {"drift": message("drift", changed)})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            alerts = root / "gmail_alerts.json"
            metadata = root / "sync_metadata.json"
            previous_alerts = b'[{"message_id":"old"}]\n'
            previous_metadata = b'{"run_id":"old"}\n'
            alerts.write_bytes(previous_alerts)
            metadata.write_bytes(previous_metadata)
            with self.assertRaises(sync.SyncError):
                sync.sync(FakeService(api), root, run_id="failed")
            self.assertEqual(alerts.read_bytes(), previous_alerts)
            self.assertEqual(metadata.read_bytes(), previous_metadata)

    def test_non_transaction_subject_is_filtered_even_when_body_looks_parseable(self):
        body = (FIXTURES / "transaction-alert-plain.txt").read_text()
        api = FakeMessages(
            {None: {"messages": [{"id": "notice"}]}},
            {"notice": message("notice", body, subject="Your HSBC Credit Card service notice")},
        )
        with tempfile.TemporaryDirectory() as td:
            result = sync.sync(FakeService(api), Path(td), run_id="filtered")
        self.assertEqual(result["matched_count"], 0)
        self.assertEqual(result["parsed_count"], 0)
        self.assertEqual(result["rejected_count"], 1)

    def test_query_excludes_spam_and_trash(self):
        body = (FIXTURES / "transaction-alert-plain.txt").read_text()
        api = FakeMessages({None: {"messages": [{"id": "a"}]}}, {"a": message("a", body)})
        with tempfile.TemporaryDirectory() as td:
            sync.sync(FakeService(api), Path(td), run_id="query")
        self.assertEqual(api.queries, [sync.QUERY])
        self.assertIn(f'subject:"{TRANSACTION_SUBJECT}"', sync.QUERY)
        self.assertIn("-in:spam", sync.QUERY)
        self.assertIn("-in:trash", sync.QUERY)

    def test_shared_mcp_credentials_are_constructed_from_realistic_schemas(self):
        calls = []
        class Credentials:
            def __init__(self, **kwargs):
                calls.append(kwargs)
                self.valid = True
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); shared = root / "shared.json"; keys = root / "keys.json"
            shared.write_text(json.dumps({"access_token": "access", "refresh_token": "refresh", "scope": "scope-a scope-b", "expiry_date": 1780000000000}))
            keys.write_text(json.dumps({"installed": {"client_id": "client", "client_secret": "secret"}}))
            credential = sync.load_credentials(root, Credentials, shared, keys)
        self.assertTrue(credential.valid)
        expected_expiry = datetime.fromtimestamp(1780000000, timezone.utc).replace(tzinfo=None)
        self.assertEqual(calls, [{"token": "access", "refresh_token": "refresh", "token_uri": "https://oauth2.googleapis.com/token", "client_id": "client", "client_secret": "secret", "scopes": ["scope-a", "scope-b"], "expiry": expected_expiry}])
        self.assertIsNone(calls[0]["expiry"].tzinfo)
        # Mirrors google-auth Credentials.expired, which compares against naive UTC.
        naive_utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.assertIsInstance(calls[0]["expiry"] < naive_utc_now, bool)

    def test_local_authorized_user_token_precedes_shared_mcp_credentials(self):
        calls = []
        class Credentials:
            @classmethod
            def from_authorized_user_file(cls, path, scopes):
                calls.append((path, scopes)); obj = cls(); obj.valid = True; return obj
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "token.json").write_text("{}")
            sync.load_credentials(root, Credentials, root / "missing", root / "missing-keys")
        self.assertEqual(Path(calls[0][0]).name, "token.json")

    def test_second_replace_failure_restores_both_canonical_files(self):
        body = (FIXTURES / "transaction-alert-plain.txt").read_text()
        api = FakeMessages({None: {"messages": [{"id": "a"}]}}, {"a": message("a", body)})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); alerts = root / "gmail_alerts.json"; metadata = root / "sync_metadata.json"
            alerts.write_text('[{"old": true}]'); metadata.write_text('{"old": true}')
            real_replace, calls = sync.os.replace, []
            def fail_second(src, dst):
                calls.append(Path(dst).name)
                if len(calls) == 2: raise OSError("second replace failed")
                real_replace(src, dst)
            with patch.object(sync.os, "replace", side_effect=fail_second):
                with self.assertRaises(sync.SyncError): sync.sync(FakeService(api), root)
            self.assertEqual(alerts.read_text(), '[{"old": true}]')
            self.assertEqual(metadata.read_text(), '{"old": true}')

    def test_api_failure_preserves_canonical_files(self):
        api = FakeMessages({None: {"messages": [{"id": "a"}]}}, {}, get_error=RuntimeError("api"))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); alerts = root / "gmail_alerts.json"; metadata = root / "sync_metadata.json"
            alerts.write_text("old alerts"); metadata.write_text("old metadata")
            with self.assertRaises(sync.SyncError): sync.sync(FakeService(api), root)
            self.assertEqual(alerts.read_text(), "old alerts")
            self.assertEqual(metadata.read_text(), "old metadata")

    def test_auth_failure_does_not_reach_sync_or_touch_caches(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); alerts = root / "gmail_alerts.json"; metadata = root / "sync_metadata.json"
            alerts.write_text("old alerts"); metadata.write_text("old metadata")
            with patch.object(sync, "build_service", side_effect=sync.SyncError("auth")):
                with self.assertRaises(sync.SyncError): sync.run(root)
            self.assertEqual(alerts.read_text(), "old alerts")
            self.assertEqual(metadata.read_text(), "old metadata")


if __name__ == "__main__":
    unittest.main()
