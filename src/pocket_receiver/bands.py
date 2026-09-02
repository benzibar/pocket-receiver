"""Small, deliberately static UK band-identification table."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Band:
    low: float
    high: float
    name: str


# More specific ranges precede broad allocations. This is an operating aid, not
# a licence or definitive band plan. Frequencies are MHz and endpoints inclusive.
UK_BANDS = (
    Band(26.965, 27.405, "CEPT CB radio"),
    Band(27.60125, 27.99125, "UK CB radio"),
    Band(28.0, 29.7, "10 m amateur"),
    Band(50.0, 52.0, "6 m amateur"),
    Band(70.0, 70.5, "4 m amateur"),
    Band(87.5, 108.0, "FM broadcast"),
    Band(108.0, 117.95, "Air navigation"),
    Band(117.975, 136.9917, "Civil airband"),
    Band(144.0, 146.0, "2 m amateur"),
    Band(156.0, 162.025, "Marine VHF"),
    Band(174.0, 230.0, "DAB broadcast"),
    Band(230.0, 400.0, "Military airband / UHF"),
    Band(430.0, 440.0, "70 cm amateur"),
    Band(446.0, 446.2, "PMR446"),
    Band(470.0, 694.0, "UHF television"),
    Band(863.0, 865.0, "Short-range devices"),
    Band(868.0, 870.0, "Short-range devices"),
    Band(1087.0, 1093.0, "1090 MHz ADS-B"),
    Band(1240.0, 1325.0, "23 cm amateur"),
)


def identify_band(frequency_mhz: float) -> str:
    for band in UK_BANDS:
        if band.low <= frequency_mhz <= band.high:
            return band.name
    return "Other / not labelled"


def quarter_wave_m(frequency_mhz: float) -> float | None:
    if frequency_mhz <= 0:
        return None
    return 299_792_458.0 / (frequency_mhz * 1_000_000.0) / 4.0


def format_antenna_length(frequency_mhz: float) -> str:
    metres = quarter_wave_m(frequency_mhz)
    if metres is None:
        return "N/A"
    if metres >= 1:
        return f"{metres:.2f} m"
    return f"{metres * 100:.1f} cm"
