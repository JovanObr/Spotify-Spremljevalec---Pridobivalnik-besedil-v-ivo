import unittest

from utils.display import format_duration


class TestDurationFormatting(unittest.TestCase):

    def test_seconds_and_minutes(self):
        self.assertEqual(format_duration(84000), "01:24")

    def test_full_song_duration(self):
        self.assertEqual(format_duration(225000), "03:45")

    def test_zero_duration(self):
        self.assertEqual(format_duration(0), "00:00")

    def test_missing_duration(self):
        self.assertEqual(format_duration(None), "--:--")

    def test_duration_over_one_hour(self):
        self.assertEqual(format_duration(3661000), "1:01:01")


if __name__ == "__main__":
    unittest.main()