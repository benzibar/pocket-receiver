from __future__ import annotations

import argparse

from textual.app import App, ComposeResult
from textual.events import Key
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header, Input, Label, Static

from pocket_receiver.receiver import AudioReceiver, ReceiverSettings
from pocket_receiver.sdr_lease import ReadsbLease, SdrLeaseError


class ChoiceField(Static, can_focus=True):
    def __init__(
        self,
        options: tuple[tuple[str, str], ...],
        value: str,
        *,
        id: str,
    ) -> None:
        self.options = options
        self._value = value
        super().__init__("", id=id)

    @property
    def value(self) -> str:
        return self._value

    def on_mount(self) -> None:
        self._render_value()

    def _render_value(self) -> None:
        for label, value in self.options:
            if value == self._value:
                self.update(label)
                return

        self.update(self._value)

    def cycle(self, direction: int) -> None:
        values = [value for _, value in self.options]

        try:
            index = values.index(self._value)
        except ValueError:
            index = 0

        self._value = values[
            (index + direction) % len(values)
        ]
        self._render_value()
from pocket_receiver.hardware_buttons import (
    KEY_PAUSE,
    KEY_SYSRQ,
    PocketTermButtons,
)


class PocketReceiver(App):
    TITLE = "Pocket Receiver"
    FIELD_IDS = ("frequency", "mode", "gain", "volume")

    CSS = '''
    Screen { layout: vertical; }
    Header { height: 1; }
    Footer { height: 1; }
    #main { padding: 0 1; }
    .row { height: 3; }
    .label { width: 12; content-align: left middle; }
    Input, ChoiceField { height: 3; }
    #frequency { width: 20; }
    #mode { width: 16; }
    #gain { width: 16; }
    #volume { width: 16; }
    #status { height: 3; padding: 1 0; }
    Input:focus, ChoiceField:focus {
        border: tall $accent;
        color: cyan;
        text-style: bold;
    }
    '''

    BINDINGS = []

    def __init__(self, frequency: float = 100.0, mode: str = "WFM") -> None:
        super().__init__()
        self.initial_frequency = frequency
        self.initial_mode = mode.upper()
        self.receiver = AudioReceiver()
        self.lease = ReadsbLease()
        self.lease_acquired = False
        self.buttons = PocketTermButtons()
        self.button_timer = None

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
                yield ChoiceField(
                    (
                        ("AM", "AM"),
                        ("NFM", "NFM"),
                        ("WFM", "WFM"),
                        ("USB", "USB"),
                        ("LSB", "LSB"),
                    ),
                    value=(
                        self.initial_mode
                        if self.initial_mode in ("AM", "NFM", "WFM", "USB", "LSB")
                        else "WFM"
                    ),
                    id="mode",
                )
            with Horizontal(classes="row"):
                yield Label("Gain", classes="label")
                yield ChoiceField(
                    (
                        ("Auto", "Auto"),
                        ("10 dB", "10"),
                        ("20 dB", "20"),
                        ("30 dB", "30"),
                        ("40 dB", "40"),
                    ),
                    value="Auto",
                    id="gain",
                )
            with Horizontal(classes="row"):
                yield Label("Volume", classes="label")
                yield ChoiceField(
                    (
                        ("25%", "25"),
                        ("50%", "50"),
                        ("75%", "75"),
                        ("100%", "100"),
                    ),
                    value="50",
                    id="volume",
                )
            yield Static("Preparing SDR...", id="status")
        yield Footer()

    def on_mount(self) -> None:
        buttons_ok = self.buttons.open()

        if buttons_ok:
            self.button_timer = self.set_interval(
                0.05,
                self._poll_hardware_buttons,
            )

        try:
            self.lease.acquire()
            self.lease_acquired = True

            button_text = (
                "Start = listen | Select = back"
                if buttons_ok
                else "PocketTerm buttons unavailable"
            )

            self.query_one("#status", Static).update(
                f"Ready | readsb paused | {button_text}"
            )

        except SdrLeaseError as exc:
            self.query_one("#status", Static).update(
                f"SDR unavailable: {exc}"
            )

    def _poll_hardware_buttons(self) -> None:
        for key_code in self.buttons.read_presses():
            if key_code == KEY_PAUSE:
                self.action_toggle()
            elif key_code == KEY_SYSRQ:
                self.action_quit_receiver()

    def _settings(self) -> ReceiverSettings:
        freq_text = self.query_one("#frequency", Input).value.strip()
        frequency = float(freq_text)
        mode = self.query_one("#mode", ChoiceField).value
        gain = self.query_one("#gain", ChoiceField).value
        volume = int(self.query_one("#volume", ChoiceField).value)
        return ReceiverSettings(frequency, mode, gain, volume)

    def _focused_field_index(self) -> int | None:
        focused = self.focused

        if focused is None:
            return None

        widget_id = focused.id

        try:
            return self.FIELD_IDS.index(widget_id)
        except ValueError:
            return None

    def _move_field_focus(self, direction: int) -> None:
        index = self._focused_field_index()

        if index is None:
            index = 0
        else:
            index = (
                index + direction
            ) % len(self.FIELD_IDS)

        self.query_one(
            f"#{self.FIELD_IDS[index]}"
        ).focus()

    def _cycle_choice(self, direction: int) -> None:
        focused = self.focused

        if isinstance(focused, ChoiceField):
            focused.cycle(direction)

    def on_key(self, event: Key) -> None:
        """PocketTerm navigation while keeping Frequency directly editable."""
        if event.key == "up":
            event.prevent_default()
            event.stop()
            self._move_field_focus(-1)
            return

        if event.key == "down":
            event.prevent_default()
            event.stop()
            self._move_field_focus(1)
            return

        if event.key == "left":
            if isinstance(self.focused, ChoiceField):
                event.prevent_default()
                event.stop()
                self._cycle_choice(-1)
            return

        if event.key == "right":
            if isinstance(self.focused, ChoiceField):
                event.prevent_default()
                event.stop()
                self._cycle_choice(1)
            return


    def action_toggle(self) -> None:
        status = self.query_one("#status", Static)
        if not self.lease_acquired:
            status.update("SDR unavailable: readsb lease not acquired")
            return
        if self.receiver.running:
            self.receiver.stop()
            status.update("Stopped | Start = listen")
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
                f"{settings.mode} | Start = stop"
            )
        except (OSError, KeyError) as exc:
            self.receiver.stop()
            status.update(f"Receiver error: {exc}")

    def action_quit_receiver(self) -> None:
        self.exit()

    def on_unmount(self) -> None:
        self.receiver.stop()
        self.buttons.close()

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
