from __future__ import annotations

import os
import struct
from pathlib import Path


EV_KEY = 0x01
KEY_SYSRQ = 99
KEY_PAUSE = 119

_INPUT_EVENT = struct.Struct("llHHI")


class PocketTermButtons:
    """Read the PocketTerm Pico keyboard's Linux evdev events directly."""

    def __init__(self) -> None:
        self.fd: int | None = None
        self.device_path: Path | None = None

    @staticmethod
    def _find_keyboard_event() -> Path | None:
        base = Path("/sys/class/input")

        for event_dir in sorted(base.glob("event*")):
            name_file = event_dir / "device" / "name"

            try:
                name = name_file.read_text(
                    encoding="utf-8"
                ).strip()
            except OSError:
                continue

            if name == "My Company My Custom Pico Keyboard":
                return Path("/dev/input") / event_dir.name

        return None

    def open(self) -> bool:
        self.close()

        path = self._find_keyboard_event()

        if path is None:
            return False

        try:
            self.fd = os.open(
                path,
                os.O_RDONLY | os.O_NONBLOCK,
            )
        except OSError:
            self.fd = None
            return False

        self.device_path = path
        return True

    def close(self) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass

        self.fd = None
        self.device_path = None

    def read_presses(self) -> list[int]:
        """Return key codes for key-down events currently waiting."""
        if self.fd is None:
            return []

        presses: list[int] = []

        while True:
            try:
                data = os.read(
                    self.fd,
                    _INPUT_EVENT.size * 32,
                )
            except BlockingIOError:
                break
            except OSError:
                break

            if not data:
                break

            usable = (
                len(data)
                // _INPUT_EVENT.size
                * _INPUT_EVENT.size
            )

            for offset in range(
                0,
                usable,
                _INPUT_EVENT.size,
            ):
                _, _, event_type, code, value = (
                    _INPUT_EVENT.unpack_from(
                        data,
                        offset,
                    )
                )

                if (
                    event_type == EV_KEY
                    and value == 1
                ):
                    presses.append(code)

        return presses
