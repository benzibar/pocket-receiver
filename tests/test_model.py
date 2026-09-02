import unittest

from pocket_receiver.model import (
    ReceiverSettings,
    bandwidth_hz,
    digits_to_frequency,
    format_frequency,
    frequency_to_digits,
)


class FrequencyTests(unittest.TestCase):
    def test_seven_digit_round_trip(self):
        self.assertEqual(frequency_to_digits(104.0), "0104000")
        self.assertEqual(format_frequency(104.0), "0,104.000")
        self.assertEqual(digits_to_frequency("0121500"), 121.5)

    def test_rejects_malformed_digits(self):
        with self.assertRaises(ValueError):
            digits_to_frequency("104.000")

    def test_bandwidth_conversion(self):
        self.assertEqual(bandwidth_hz("12.5 kHz"), 12_500)

    def test_mode_changes_to_safe_default_bandwidth(self):
        settings = ReceiverSettings().with_mode("AM")
        self.assertEqual(settings.bandwidth, "12 kHz")
        settings.validated()

    def test_invalid_cross_mode_bandwidth_is_rejected(self):
        with self.assertRaises(ValueError):
            ReceiverSettings(mode="AM", bandwidth="200 kHz").validated()


if __name__ == "__main__":
    unittest.main()

