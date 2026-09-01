from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ReceiverSettings:
    frequency_mhz: float
    mode: str
    gain: str
    volume: int


MODE_ARGS = {
    "AM": ["-M", "am", "-s", "12000", "-r", "48000"],
    "NFM": ["-M", "fm", "-s", "12000", "-r", "48000"],
    "WFM": ["-M", "wbfm", "-s", "200000", "-r", "48000"],
    "USB": ["-M", "usb", "-s", "12000", "-r", "48000"],
    "LSB": ["-M", "lsb", "-s", "12000", "-r", "48000"],
}


class AudioReceiver:
    def __init__(self) -> None:
        self.rtl_fm: subprocess.Popen | None = None
        self.aplay: subprocess.Popen | None = None

    @property
    def running(self) -> bool:
        return self.rtl_fm is not None and self.rtl_fm.poll() is None

    def set_volume(self, percent: int) -> None:
        for control in ("Master", "PCM", "Speaker", "Headphone"):
            result = subprocess.run(
                ["amixer", "-q", "sset", control, f"{percent}%"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0:
                return

    def start(self, settings: ReceiverSettings) -> None:
        self.stop()
        self.set_volume(settings.volume)

        freq_hz = int(settings.frequency_mhz * 1_000_000)
        cmd = ["rtl_fm", "-f", str(freq_hz)]
        cmd.extend(MODE_ARGS[settings.mode])
        if settings.gain != "Auto":
            cmd.extend(["-g", settings.gain])

        self.rtl_fm = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert self.rtl_fm.stdout is not None
        self.aplay = subprocess.Popen(
            ["aplay", "-q", "-r", "48000", "-f", "S16_LE", "-c", "1"],
            stdin=self.rtl_fm.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        for proc in (self.aplay, self.rtl_fm):
            if proc is not None and proc.poll() is None:
                proc.terminate()
        for proc in (self.aplay, self.rtl_fm):
            if proc is not None:
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
        self.aplay = None
        self.rtl_fm = None
