import unittest
from unittest.mock import patch

import sync_alerts


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeMessages:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return FakeRequest(next(self.pages))


class FakeUsers:
    def __init__(self, messages):
        self._messages = messages

    def messages(self):
        return self._messages


class FakeService:
    def __init__(self, pages):
        self.messages = FakeMessages(pages)

    def users(self):
        return FakeUsers(self.messages)


class SyncAlertsTests(unittest.TestCase):
    def test_parses_one_decimal_axis_amount_without_truncation(self):
        self.assertEqual(sync_alerts.parse_alert_amount("INR 944.7 spent on credit card no. XX3164"), 944.7)

    def test_paginates_matching_messages(self):
        service = FakeService([
            {"messages": [{"id": "a"}, {"id": "b"}], "nextPageToken": "next"},
            {"messages": [{"id": "c"}]},
        ])

        ids = sync_alerts.list_matching_message_ids(service, "query", max_messages=500)

        self.assertEqual(ids, ["a", "b", "c"])
        self.assertEqual(service.messages.calls[0]["maxResults"], 100)
        self.assertEqual(service.messages.calls[1]["pageToken"], "next")

    def test_stops_at_explicit_safety_ceiling(self):
        service = FakeService([
            {"messages": [{"id": str(index)} for index in range(100)], "nextPageToken": "next"},
            {"messages": [{"id": str(index)} for index in range(100, 200)], "nextPageToken": "more"},
        ])

        ids = sync_alerts.list_matching_message_ids(service, "query", max_messages=150)

        self.assertEqual(len(ids), 150)
        self.assertEqual(len(service.messages.calls), 2)

    @patch.object(sync_alerts, "get_gmail_service", return_value=None)
    def test_authentication_failure_returns_nonzero(self, _service):
        self.assertEqual(sync_alerts.main(), 1)


if __name__ == "__main__":
    unittest.main()
