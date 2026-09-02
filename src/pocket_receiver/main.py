"""Command-line entry point."""

from __future__ import annotations

import argparse
import signal
import sys

from . import __version__
from .lease import ReadsbLease
from .model import BANDWIDTHS, DEFAULT_BANDWIDTH, GAIN_CHOICES, MODES, ReceiverSettings
from .receiver import ReceiverPipeline


def normalize_bandwidth(value: str, mode: str) -> str:
    cleaned = value.strip().lower().replace("khz", "").replace(" ", "")
    try:
        number = float(cleaned)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bandwidth must be a number in kHz") from exc
    for label in BANDWIDTHS[mode]:
        if abs(float(label.split()[0]) - number) < 0.001:
            return label
    allowed = ", ".join(BANDWIDTHS[mode])
    raise argparse.ArgumentTypeError(f"bandwidth for {mode} must be one of {allowed}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pocket-receiver",
        description="Keyboard-first RTL-SDR receiver for Raspberry Pi/PocketTerm",
    )
    parser.add_argument("-f", "--frequency", type=float, default=104.0, metavar="MHZ")
    parser.add_argument("-m", "--mode", type=str.upper, choices=MODES, default="WFM")
    parser.add_argument("-b", "--bandwidth", metavar="KHZ", help="mode-appropriate bandwidth")
    parser.add_argument("-g", "--gain", default="Auto", metavar="GAIN", help="Auto, 20, 40, 60 or 80")
    parser.add_argument("-v", "--volume", type=int, choices=range(0, 101, 10), default=30)
    parser.add_argument("-d", "--device", type=int, default=0, help="RTL-SDR device index")
    parser.add_argument("--audio-device", default="default", help="ALSA PCM device")
    parser.add_argument("--play", action="store_true", help="start receiving immediately")
    parser.add_argument("--no-readsb", action="store_true", help="do not stop/restore readsb")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def settings_from_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> ReceiverSettings:
    mode = args.mode.upper()
    bandwidth = DEFAULT_BANDWIDTH[mode]
    if args.bandwidth is not None:
        try:
            bandwidth = normalize_bandwidth(args.bandwidth, mode)
        except argparse.ArgumentTypeError as exc:
            parser.error(str(exc))
    gain = "Auto" if str(args.gain).lower() == "auto" else str(args.gain)
    if gain not in GAIN_CHOICES:
        parser.error(f"gain must be one of {', '.join(GAIN_CHOICES)}")
    try:
        return ReceiverSettings(
            frequency_mhz=args.frequency,
            mode=mode,
            bandwidth=bandwidth,
            gain=gain,
            volume=args.volume,
        ).validated()
    except ValueError as exc:
        parser.error(str(exc))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = settings_from_args(args, parser)
    lease = ReadsbLease(enabled=not args.no_readsb)
    pipeline = ReceiverPipeline(
        settings=settings,
        device=args.device,
        audio_device=args.audio_device,
        lease=lease,
    )

    def request_shutdown(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    # Closing an SSH session or stopping a launcher should still reap audio
    # children and return the RTL-SDR lease to readsb.
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    try:
        from .ui import run_ui
        run_ui(pipeline, autoplay=args.play)
    except KeyboardInterrupt:
        pipeline.close()
    except Exception as exc:
        pipeline.close()
        print(f"pocket-receiver: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
