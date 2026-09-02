import unittest

from pocket_receiver.bands import format_antenna_length, identify_band, quarter_wave_m


class BandTests(unittest.TestCase):
    def test_common_uk_allocations(self):
        self.assertEqual(identify_band(104.0), "FM broadcast")
        self.assertEqual(identify_band(121.5), "Civil airband")
        self.assertEqual(identify_band(145.5), "2 m amateur")
        self.assertEqual(identify_band(446.00625), "PMR446")

    def test_quarter_wave(self):
        self.assertAlmostEqual(quarter_wave_m(100.0), 0.74948, places=4)
        self.assertEqual(format_antenna_length(100.0), "74.9 cm")


if __name__ == "__main__":
    unittest.main()

