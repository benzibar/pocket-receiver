from __future__ import annotations

import argparse

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header, Input, Label, Select, Static

from pocket_receiver.receiver import AudioReceiver, ReceiverSettings
from pocket_receiver.sdr_lease import ReadsbLease, SdrLeaseError


class PocketReceiver(App):
    TITLE = "Pocket Receiver"

    CSS = '''
    Screen { layout: vertical; }
    Header { height: 1; }
    Footer { height: 1; }
    #main { padding: 0 1; }
    .row { height: 3; }
    .label { width: 12; content-align: left middle; }
    Input, Select { height: 3; }
    #frequency { width: 20; }
    #mode { width: 16; }
    #gain { width: 16; }
    #volume { width: 16; }
    #status { height: 3; padding: 1 0; }
    '''

    BINDINGS = [
        Binding("l", "toggle", "Listen/Stop", priority=True),
        Binding("q", "quit_receiver", "Back", priority=True),
    ]

    def __init__(self, frequency: float = 100.0, mode: str = "WFM") -> None:
        super().__init__()
        self.initial_frequency = frequency
        self.initial_mode = mode.upper()
        self.receiver = AudioReceiver()
        self.lease = ReadsbLease()
        self.lease_acquired = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Container(id="main"):
            with Horizontal(classes="row"):
                yield Label("Frequency", classes="label")
                yield Input(
                    value=f"{self.initial_frequency:.3f}",
                    placeholder="MHz",
                    id="frequency",
                )
            with Horizontal(classes="row"):
                yield Label("Mode", classes="label")
                yield Select(
                    [(x, x) for x in ("AM", "NFM", "WFM", "USB", "LSB")],
                    value=self.initial_mode if self.initial_mode in
                    ("AM", "NFM", "WFM", "USB", "LSB") else "WFM",
                    id="mode",
                    allow_blank=False,
                )
            with Horizontal(classes="row"):
                yield Label("Gain", classes="label")
                yield Select(
                    [(x, x) for x in ("Auto", "10", "20", "30", "40")],
                    value="Auto",
                    id="gain",
                    allow_blank=False,
                )
            with Horizontal(classes="row"):
                yield Label("Volume", classes="label")
                yield Select(
                    [(f"{x}%", x) for x in (25, 50, 75, 100)],
                    value=50,
                    id="volume",
                    allow_blank=False,
                )
            yield Static("Preparing SDR...", id="status")
        yield Footer()

    def on_mount(self) -> None:
        try:
            self.lease.acquire()
            self.lease_acquired = True
            self.query_one("#status", Static).update(
                "Ready | readsb paused | L = listen"
            )
        except SdrLeaseError as exc:
            self.query_one("#status", Static).update(f"SDR unavailable: {exc}")

    def _settings(self) -> ReceiverSettings:
        freq_text = self.query_one("#frequency", Input).value.strip()
        frequency = float(freq_text)
        mode = str(self.query_one("#mode", Select).value)
        gain = str(self.query_one("#gain", Select).value)
        volume = int(self.query_one("#volume", Select).value)
        return ReceiverSettings(frequency, mode, gain, volume)

    def action_toggle(self) -> None:
        status = self.query_one("#status", Static)
        if not self.lease_acquired:
            status.update("SDR unavailable: readsb lease not acquired")
            return
        if self.receiver.running:
            self.receiver.stop()
            status.update("Stopped | L = listen")
            return
        try:
            settings = self._settings()
            if settings.frequency_mhz <= 0:
                raise ValueError
        except (ValueError, TypeError):
            status.update("Invalid frequency")
            return
        try:
            self.receiver.start(settings)
            status.update(
                f"Listening {settings.frequency_mhz:.3f} MHz "
                f"{settings.mode} | L = stop"
            )
        except (OSError, KeyError) as exc:
            self.receiver.stop()
            status.update(f"Receiver error: {exc}")

    def action_quit_receiver(self) -> None:
        self.exit()

    def on_unmount(self) -> None:
        self.receiver.stop()
        if self.lease_acquired:
            try:
                self.lease.release()
            except SdrLeaseError:
                pass
            finally:
                self.lease_acquired = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frequency", type=float, default=100.0)
    parser.add_argument(
        "--mode",
        choices=["AM", "NFM", "WFM", "USB", "LSB",
                 "am", "nfm", "wfm", "usb", "lsb"],
        default="WFM",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    PocketReceiver(args.frequency, args.mode).run()


if __name__ == "__main__":
    main()
