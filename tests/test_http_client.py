"""Test resilient API request behavior without network calls."""

import unittest
from unittest.mock import Mock, call, patch

import requests

from extract.http_client import get_json_with_retry


def mock_response(status_code, payload=None, headers=None):
    """Return a mocked requests response."""
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = payload or {}

    if status_code >= 400:
        error = requests.HTTPError(f"HTTP {status_code}", response=response)
        response.raise_for_status.side_effect = error

    return response


class GetJsonWithRetryTests(unittest.TestCase):
    @patch("extract.http_client.time.sleep")
    @patch("extract.http_client.requests.get")
    def test_retries_transient_status_then_returns_json(self, request_get, sleep):
        request_get.side_effect = [
            mock_response(503),
            mock_response(200, {"results": [1]}),
        ]

        result = get_json_with_retry(
            "https://example.test",
            source_name="Test API",
        )

        self.assertEqual(result, {"results": [1]})
        self.assertEqual(request_get.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch("extract.http_client.time.sleep")
    @patch("extract.http_client.requests.get")
    def test_respects_retry_after_header(self, request_get, sleep):
        request_get.side_effect = [
            mock_response(429, headers={"Retry-After": "7"}),
            mock_response(200, {"ok": True}),
        ]

        result = get_json_with_retry(
            "https://example.test",
            source_name="Test API",
        )

        self.assertEqual(result, {"ok": True})
        sleep.assert_called_once_with(7.0)

    @patch("extract.http_client.time.sleep")
    @patch("extract.http_client.requests.get")
    def test_does_not_retry_permanent_client_error(self, request_get, sleep):
        request_get.return_value = mock_response(401)

        with self.assertRaises(requests.HTTPError):
            get_json_with_retry(
                "https://example.test",
                source_name="Test API",
            )

        request_get.assert_called_once()
        sleep.assert_not_called()

    @patch("extract.http_client.time.sleep")
    @patch("extract.http_client.requests.get")
    def test_raises_after_network_retries_are_exhausted(self, request_get, sleep):
        request_get.side_effect = [
            requests.Timeout("timeout"),
            requests.Timeout("timeout"),
            requests.Timeout("timeout"),
        ]

        with self.assertRaises(requests.Timeout):
            get_json_with_retry(
                "https://example.test",
                source_name="Test API",
            )

        self.assertEqual(request_get.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(1), call(2)])


if __name__ == "__main__":
    unittest.main()
