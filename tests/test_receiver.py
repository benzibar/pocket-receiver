import array
import unittest
from unittest.mock import Mock, patch

from pocket_receiver.model import ReceiverSettings
from pocket_receiver.receiver import (
    ReceiverPipeline,
    pcm_level_dbfs,
)


class ReceiverCommandTests(unittest.TestCase):
    def test_pcm_level_is_measured_in_dbfs(self):
        self.assertEqual(
            pcm_level_dbfs(
                array.array("h", [0, 0, 0])
            ),
            -96.0,
        )

        self.assertAlmostEqual(
            pcm_level_dbfs(
                array.array(
                    "h",
                    [16384, -16384],
                )
            ),
            -6.0206,
            places=3,
        )

    def test_idle_sdr_status_is_truthful(self):
        pipeline = ReceiverPipeline(
            ReceiverSettings(),
            device=2,
        )

        self.assertEqual(
            pipeline.sdr_status,
            "RTL-SDR #2 · standby",
        )

    def test_wfm_command_contains_all_selected_parameters(self):
        pipeline = ReceiverPipeline(
            ReceiverSettings(
                frequency_mhz=104.0,
                mode="WFM",
                bandwidth="200 kHz",
                gain="40",
                volume=30,
            ),
            device=1,
        )

        command = pipeline._rtl_command()

        self.assertEqual(
            command[0],
            "rtl_fm",
        )

        self.assertIn(
            "104000000",
            command,
        )

        self.assertIn(
            "wfm",
            command,
        )

        self.assertIn(
            "200000",
            command,
        )

        self.assertIn(
            "40",
            command,
        )

        self.assertIn(
            "deemp",
            command,
        )

    @patch(
        "pocket_receiver.receiver.subprocess.run"
    )
    def test_system_volume_uses_master_when_available(
        self,
        run,
    ):
        run.side_effect = [
            Mock(
                returncode=0,
                stdout=(
                    "Simple mixer control "
                    "'Master',0\n"
                ),
                stderr="",
            ),
            Mock(
                returncode=0,
                stdout="",
                stderr="",
            ),
        ]

        pipeline = ReceiverPipeline(
            ReceiverSettings(
                volume=100
            )
        )

        pipeline._set_system_volume(100)

        self.assertEqual(
            run.call_args_list[0].args[0],
            [
                "amixer",
                "scontrols",
            ],
        )

        self.assertEqual(
            run.call_args_list[1].args[0],
            [
                "amixer",
                "set",
                "Master",
                "100%",
            ],
        )

        self.assertFalse(
            run.call_args_list[1].kwargs[
                "check"
            ]
        )

    @patch(
        "pocket_receiver.receiver.subprocess.run"
    )
    def test_system_volume_falls_back_to_pcm(
        self,
        run,
    ):
        run.side_effect = [
            Mock(
                returncode=0,
                stdout=(
                    "Simple mixer control "
                    "'PCM',0\n"
                ),
                stderr="",
            ),
            Mock(
                returncode=0,
                stdout="",
                stderr="",
            ),
        ]

        pipeline = ReceiverPipeline(
            ReceiverSettings(
                volume=70
            )
        )

        pipeline._set_system_volume(70)

        self.assertEqual(
            run.call_args_list[0].args[0],
            [
                "amixer",
                "scontrols",
            ],
        )

        self.assertEqual(
            run.call_args_list[1].args[0],
            [
                "amixer",
                "set",
                "PCM",
                "70%",
            ],
        )

        self.assertFalse(
            run.call_args_list[1].kwargs[
                "check"
            ]
        )

    @patch(
        "pocket_receiver.receiver.subprocess.run"
    )
    def test_missing_supported_mixer_control_raises(
        self,
        run,
    ):
        run.return_value = Mock(
            returncode=0,
            stdout=(
                "Simple mixer control "
                "'Headphone',0\n"
            ),
            stderr="",
        )

        pipeline = ReceiverPipeline(
            ReceiverSettings()
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "No supported ALSA volume control",
        ):
            pipeline._set_system_volume(50)

    def test_auto_gain_omits_gain_flag(self):
        command = ReceiverPipeline(
            ReceiverSettings()
        )._rtl_command()

        self.assertNotIn(
            "-g",
            command,
        )


if __name__ == "__main__":
    unittest.main()
