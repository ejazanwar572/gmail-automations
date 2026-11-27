import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import alert_ingestion as ai


class AlertIngestionTests(unittest.TestCase):
    def test_fixture_alert_adapter(self):
        sample_messages = [
            {"id": "msg1", "internalDate": "1783000000000", "payload": {}},
            {"id": "msg2", "internalDate": "1783000010000", "payload": {}},
        ]
        adapter = ai.FixtureAlertAdapter(sample_messages)
        ids, messages = adapter.fetch_messages_for_query("some query")
        self.assertEqual(ids, ["msg1", "msg2"])
        self.assertEqual(len(messages), 2)

    def test_mime_decoding(self):
        payload_plain = {
            "mimeType": "text/plain",
            "body": {"data": ai.base64.urlsafe_b64encode(b"Hello world").decode()},
        }
        self.assertEqual(ai.decode_message_body(payload_plain), "Hello world")

        payload_html = {
            "mimeType": "text/html",
            "body": {"data": ai.base64.urlsafe_b64encode(b"<p>Hello<br>world</p>").decode()},
        }
        self.assertIn("Hello\nworld", ai.decode_message_body(payload_html))

    def test_atomic_write_cache_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            alerts = [{"message_id": "1", "amount": 100.0}]
            metadata = {"run_id": "test-run", "alert_count": 1}
            ai.atomic_write_cache(root, alerts, metadata)

            self.assertTrue((root / "gmail_alerts.json").exists())
            self.assertTrue((root / "sync_metadata.json").exists())
            loaded_alerts = json.loads((root / "gmail_alerts.json").read_text())
            self.assertEqual(loaded_alerts[0]["amount"], 100.0)


    def test_build_service_refreshes_when_invalid_with_refresh_token(self):
        from unittest.mock import MagicMock, patch
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = False
        mock_creds.refresh_token = "valid_refresh_token"

        def do_refresh(req):
            mock_creds.valid = True

        mock_creds.refresh.side_effect = do_refresh

        with patch("alert_ingestion.load_credentials", return_value=mock_creds), \
             patch("googleapiclient.discovery.build") as mock_build:
            ai.build_service(Path("/tmp"))
            self.assertTrue(mock_creds.refresh.called)
            mock_build.assert_called_once()

    def test_build_service_raises_when_no_refresh_token_and_invalid(self):
        from unittest.mock import MagicMock, patch
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = False
        mock_creds.refresh_token = None

        with patch("alert_ingestion.load_credentials", return_value=mock_creds):
            with self.assertRaises(ai.SyncError) as ctx:
                ai.build_service(Path("/tmp"))
            self.assertIn("lack a refresh_token", str(ctx.exception))

    def test_build_service_raises_when_refresh_fails(self):
        from unittest.mock import MagicMock, patch
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = False
        mock_creds.refresh_token = "valid_refresh_token"
        mock_creds.refresh.side_effect = Exception("invalid_grant: Token has been revoked")

        with patch("alert_ingestion.load_credentials", return_value=mock_creds):
            with self.assertRaises(ai.SyncError) as ctx:
                ai.build_service(Path("/tmp"))
            self.assertIn("Gmail token refresh failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
