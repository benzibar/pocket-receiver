"""Receiver settings and validation."""

from __future__ import annotations

from dataclasses import dataclass, replace


MODES = ("AM", "NFM", "WFM", "USB", "LSB")
GAIN_CHOICES = ("Auto", "20", "40", "60", "80")
BANDWIDTHS = {
    "AM": ("6 kHz", "9 kHz", "12 kHz", "15 kHz"),
    "NFM": ("6.25 kHz", "8.33 kHz", "12.5 kHz", "25 kHz"),
    "WFM": ("100 kHz", "150 kHz", "200 kHz", "250 kHz"),
    "USB": ("2.4 kHz", "2.7 kHz", "3 kHz"),
    "LSB": ("2.4 kHz", "2.7 kHz", "3 kHz"),
}
DEFAULT_BANDWIDTH = {
    "AM": "12 kHz",
    "NFM": "12.5 kHz",
    "WFM": "200 kHz",
    "USB": "2.7 kHz",
    "LSB": "2.7 kHz",
}


def bandwidth_hz(label: str) -> int:
    number, unit = label.split()
    value = float(number)
    return round(value * (1000 if unit.lower() == "khz" else 1))


def frequency_to_digits(mhz: float) -> str:
    """Return seven digits representing MMMM.mmm MHz."""
    khz = round(mhz * 1000)
    if not 0 <= khz <= 9_999_999:
        raise ValueError("frequency must fit the 0,000.000 display")
    return f"{khz:07d}"


def digits_to_frequency(digits: str) -> float:
    if len(digits) != 7 or not digits.isdigit():
        raise ValueError("frequency must contain exactly seven digits")
    return int(digits) / 1000.0


def format_frequency(value: float | str) -> str:
    digits = value if isinstance(value, str) else frequency_to_digits(value)
    if len(digits) != 7 or not digits.isdigit():
        raise ValueError("frequency must contain exactly seven digits")
    return f"{digits[0]},{digits[1:4]}.{digits[4:]}"


@dataclass(frozen=True)
class ReceiverSettings:
    frequency_mhz: float = 104.0
    mode: str = "WFM"
    bandwidth: str = "200 kHz"
    gain: str = "Auto"
    volume: int = 30

    def validated(self) -> "ReceiverSettings":
        mode = self.mode.upper()
        if mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}")
        if not 24.0 <= self.frequency_mhz <= 1766.0:
            raise ValueError("frequency must be within the typical RTL-SDR range (24-1766 MHz)")
        if self.bandwidth not in BANDWIDTHS[mode]:
            raise ValueError(
                f"bandwidth for {mode} must be one of {', '.join(BANDWIDTHS[mode])}"
            )
        gain = "Auto" if self.gain.lower() == "auto" else self.gain
        if gain not in GAIN_CHOICES:
            raise ValueError(f"gain must be one of {', '.join(GAIN_CHOICES)}")
        if self.volume not in range(0, 101, 10):
            raise ValueError("volume must be 0-100 in steps of 10")
        return replace(self, mode=mode, gain=gain)

    def with_mode(self, mode: str) -> "ReceiverSettings":
        mode = mode.upper()
        return replace(self, mode=mode, bandwidth=DEFAULT_BANDWIDTH[mode])

