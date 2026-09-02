import unittest

from pocket_receiver.main import build_parser, normalize_bandwidth, settings_from_args


class CliTests(unittest.TestCase):
    def test_parameterized_launch(self):
        parser = build_parser()
        args = parser.parse_args([
            "--frequency", "121.5", "--mode", "am", "--bandwidth", "12",
            "--gain", "40", "--volume", "50", "--play",
        ])
        settings = settings_from_args(args, parser)
        self.assertEqual(settings.frequency_mhz, 121.5)
        self.assertEqual(settings.mode, "AM")
        self.assertEqual(settings.bandwidth, "12 kHz")
        self.assertEqual(settings.gain, "40")
        self.assertTrue(args.play)

    def test_bandwidth_normalizer_accepts_suffix(self):
        self.assertEqual(normalize_bandwidth("12.5kHz", "NFM"), "12.5 kHz")


if __name__ == "__main__":
    unittest.main()

