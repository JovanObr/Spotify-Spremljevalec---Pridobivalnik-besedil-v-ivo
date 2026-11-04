import unittest
from types import SimpleNamespace
from unittest.mock import patch

from utils.spotify_errors import get_retry_delay


class TestSpotifyErrors(unittest.TestCase):

    @patch("builtins.print")
    def test_unauthorized_stops_application(self, mock_print):
        error = SimpleNamespace(http_status=401)

        result = get_retry_delay(error)

        self.assertIsNone(result)

    @patch("builtins.print")
    def test_forbidden_stops_application(self, mock_print):
        error = SimpleNamespace(http_status=403)

        result = get_retry_delay(error)

        self.assertIsNone(result)

    @patch("builtins.print")
    def test_rate_limit_uses_retry_after(self, mock_print):
        error = SimpleNamespace(
            http_status=429,
            headers={"Retry-After": "45"},
        )

        result = get_retry_delay(error)

        self.assertEqual(result, 45)

    @patch("builtins.print")
    def test_rate_limit_uses_default_when_header_missing(self, mock_print):
        error = SimpleNamespace(
            http_status=429,
            headers={},
        )

        result = get_retry_delay(error)

        self.assertEqual(result, 30)

    @patch("builtins.print")
    def test_server_error_retries_after_30_seconds(self, mock_print):
        error = SimpleNamespace(http_status=503)

        result = get_retry_delay(error)

        self.assertEqual(result, 30)

    @patch("builtins.print")
    def test_other_error_retries_after_15_seconds(self, mock_print):
        error = SimpleNamespace(http_status=400)

        result = get_retry_delay(error)

        self.assertEqual(result, 15)

    @patch("builtins.print")
    def test_rate_limit_accepts_lowercase_header(self, mock_print):
        error = SimpleNamespace(
            http_status=429,
            headers={"retry-after": "60"},
        )

        result = get_retry_delay(error)

        self.assertEqual(result, 60)

    @patch("builtins.print")
    def test_rate_limit_handles_invalid_header(self, mock_print):
        error = SimpleNamespace(
            http_status=429,
            headers={"Retry-After": "invalid"},
        )

        result = get_retry_delay(error)

        self.assertEqual(result, 30)

if __name__ == "__main__":
    unittest.main()