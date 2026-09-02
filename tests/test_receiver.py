import unittest

from pocket_receiver.model import ReceiverSettings
from pocket_receiver.receiver import ReceiverPipeline


class ReceiverCommandTests(unittest.TestCase):
    def test_wfm_command_contains_all_selected_parameters(self):
        pipeline = ReceiverPipeline(ReceiverSettings(
            frequency_mhz=104.0,
            mode="WFM",
            bandwidth="200 kHz",
            gain="40",
            volume=30,
        ), device=1)
        command = pipeline._rtl_command()
        self.assertEqual(command[0], "rtl_fm")
        self.assertIn("104000000", command)
        self.assertIn("wfm", command)
        self.assertIn("200000", command)
        self.assertIn("40", command)
        self.assertIn("deemp", command)

    def test_auto_gain_omits_gain_flag(self):
        command = ReceiverPipeline(ReceiverSettings())._rtl_command()
        self.assertNotIn("-g", command)


if __name__ == "__main__":
    unittest.main()

