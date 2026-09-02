"""Curses UI designed for an 80x30 (640x480) PocketTerm console."""

from __future__ import annotations

import curses
import time
from dataclasses import replace

from .bands import format_antenna_length, identify_band
from .model import (
    BANDWIDTHS,
    DEFAULT_BANDWIDTH,
    GAIN_CHOICES,
    MODES,
    ReceiverSettings,
    digits_to_frequency,
    format_frequency,
    frequency_to_digits,
)
from .receiver import ReceiverPipeline


FIELDS = ("Frequency", "Mode", "Bandwidth", "Gain")


class PocketReceiverUI:
    def __init__(self, screen: curses.window, pipeline: ReceiverPipeline, autoplay: bool = False):
        self.screen = screen
        self.pipeline = pipeline
        self.settings = pipeline.settings
        self.focus = 0
        self.editing = False
        self.menu_index = 0
        self.frequency_digits = frequency_to_digits(self.settings.frequency_mhz)
        self.digit_index = 0
        self.retune_at: float | None = None
        self.message = "Ready — Enter edits the highlighted field"
        self.running = True
        self.autoplay = autoplay
        pipeline.report = self._report
        if pipeline.lease:
            pipeline.lease.report = self._report

    def _report(self, message: str) -> None:
        self.message = message.replace("\n", " ")[:76]

    @staticmethod
    def _safe_add(screen: curses.window, y: int, x: int, text: str, attr: int = 0) -> None:
        height, width = screen.getmaxyx()
        if 0 <= y < height and x < width:
            try:
                screen.addnstr(y, max(0, x), text, max(0, width - max(0, x) - 1), attr)
            except curses.error:
                pass

    def _init_screen(self) -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(True)
        self.screen.timeout(50)
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
            except curses.error:
                pass
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(3, curses.COLOR_GREEN, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_RED, -1)

    def run(self) -> None:
        self._init_screen()
        if self.autoplay:
            self._toggle_play()
        try:
            while self.running:
                self._handle_pending_retune()
                self._draw()
                key = self.screen.getch()
                if key != -1:
                    self._handle_key(key)
        finally:
            self.pipeline.close()

    def _draw_box(self, y: int, x: int, height: int, width: int, title: str = "") -> None:
        attr = curses.color_pair(1)
        self._safe_add(self.screen, y, x, "+" + "-" * (width - 2) + "+", attr)
        for row in range(y + 1, y + height - 1):
            self._safe_add(self.screen, row, x, "|", attr)
            self._safe_add(self.screen, row, x + width - 1, "|", attr)
        self._safe_add(self.screen, y + height - 1, x, "+" + "-" * (width - 2) + "+", attr)
        if title:
            self._safe_add(self.screen, y, x + 2, f" {title} ", attr | curses.A_BOLD)

    def _field_value(self, index: int) -> str:
        if index == 0:
            return format_frequency(self.frequency_digits) + " MHz"
        if index == 1:
            return self.settings.mode
        if index == 2:
            return self.settings.bandwidth
        return self.settings.gain

    def _draw_frequency_value(self, y: int, x: int, attr: int) -> None:
        display = format_frequency(self.frequency_digits)
        if not (self.editing and self.focus == 0):
            self._safe_add(self.screen, y, x, display + " MHz", attr)
            return
        digit_positions = (0, 2, 3, 4, 6, 7, 8)
        self._safe_add(self.screen, y, x, display + " MHz", attr)
        selected_x = x + digit_positions[self.digit_index]
        self._safe_add(self.screen, y, selected_x, display[digit_positions[self.digit_index]], curses.color_pair(2) | curses.A_BOLD)

    def _draw(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        if height < 22 or width < 64:
            self._safe_add(self.screen, 0, 0, f"Pocket Receiver needs at least 64x22; current {width}x{height}", curses.A_BOLD)
            self._safe_add(self.screen, 2, 0, "Resize the terminal, or press q to quit.")
            self.screen.refresh()
            return

        left_width = min(35, width // 2 - 2)
        right_x = left_width + 2
        right_width = width - right_x - 1
        title_attr = curses.color_pair(1) | curses.A_BOLD
        state_attr = curses.color_pair(3) if self.pipeline.playing else curses.color_pair(4)
        state = "PLAYING" if self.pipeline.playing else "PAUSED"
        self._safe_add(self.screen, 1, 2, "POCKET RECEIVER", title_attr)
        self._safe_add(self.screen, 1, max(2, width - len(state) - 3), state, state_attr | curses.A_BOLD)

        field_rows = (5, 9, 13, 17)
        for index, (label, row) in enumerate(zip(FIELDS, field_rows)):
            focused = index == self.focus
            attr = curses.color_pair(2) | curses.A_BOLD if focused and not (self.editing and index == 0) else curses.A_BOLD
            marker = ">" if focused else " "
            self._safe_add(self.screen, row, 2, f"{marker} {label:<10}", curses.color_pair(1) if focused else 0)
            self._safe_add(self.screen, row - 1, 15, "+----------------+")
            self._safe_add(self.screen, row, 15, "|                |")
            self._safe_add(self.screen, row + 1, 15, "+----------------+")
            if index == 0:
                self._draw_frequency_value(row, 18, attr)
            else:
                value = self._field_value(index)
                self._safe_add(self.screen, row, 18, value[:12], attr)

        self._draw_box(3, right_x, 16, right_width, "INFORMATION")
        info_x = right_x + 3
        info = (
            ("Quarter wave", format_antenna_length(self.settings.frequency_mhz)),
            ("UK band", identify_band(self.settings.frequency_mhz)),
            ("RSSI", "N/A (rtl_fm)"),
            ("SNR", "N/A (rtl_fm)"),
            ("Volume", f"{self.settings.volume}%"),
        )
        for offset, (label, value) in enumerate(info):
            row = 5 + offset * 2
            self._safe_add(self.screen, row, info_x, f"{label}:", curses.color_pair(1) | curses.A_BOLD)
            self._safe_add(self.screen, row + 1, info_x + 2, value, curses.A_BOLD if offset in (0, 1) else 0)

        if self.editing and self.focus > 0:
            menu_height = len(self._choices()) + 2
            menu_y = field_rows[self.focus] + 2
            # Leave the final three rows for help/status. On shorter console
            # configurations, open the menu above the field instead of clipping.
            if menu_y + menu_height > height - 3:
                menu_y = max(2, field_rows[self.focus] - menu_height)
            self._draw_menu(menu_y, 17)

        help_y = height - 3
        help_parts = (
            ("q", curses.color_pair(4) | curses.A_BOLD),
            (" Quit   ", 0),
            ("Enter", curses.color_pair(4) | curses.A_BOLD),
            (" Edit/commit   ", 0),
            ("p", curses.color_pair(4) | curses.A_BOLD),
            (" Play/pause   ", 0),
            ("m/n", curses.color_pair(4) | curses.A_BOLD),
            (" Vol +/-", 0),
        )
        help_x = 2
        for text, attr in help_parts:
            self._safe_add(self.screen, help_y, help_x, text, attr)
            help_x += len(text)
        msg_attr = curses.color_pair(5) if any(w in self.message.lower() for w in ("error", "could not", "missing", "stopped:")) else curses.color_pair(4)
        self._safe_add(self.screen, height - 2, 2, self.message, msg_attr)
        self.screen.refresh()

    def _choices(self) -> tuple[str, ...]:
        if self.focus == 1:
            return MODES
        if self.focus == 2:
            return BANDWIDTHS[self.settings.mode]
        return GAIN_CHOICES

    def _draw_menu(self, y: int, x: int) -> None:
        choices = self._choices()
        width = max(len(choice) for choice in choices) + 4
        self._draw_box(y, x, len(choices) + 2, width)
        for index, choice in enumerate(choices):
            attr = curses.color_pair(2) | curses.A_BOLD if index == self.menu_index else 0
            self._safe_add(self.screen, y + 1 + index, x + 1, f" {choice:<{width - 3}}", attr)

    def _handle_key(self, key: int) -> None:
        # These receiver controls remain independent of field editing.
        if key in (ord("p"), ord("P")):
            self._toggle_play()
            return
        if key in (ord("m"), ord("M")):
            self._change_volume(10)
            return
        if key in (ord("n"), ord("N")):
            self._change_volume(-10)
            return
        if not self.editing and key in (ord("q"), ord("Q")):
            self.running = False
            return

        if not self.editing:
            if key in (curses.KEY_UP, ord("k")):
                self.focus = (self.focus - 1) % len(FIELDS)
            elif key in (curses.KEY_DOWN, ord("j"), 9):
                self.focus = (self.focus + 1) % len(FIELDS)
            elif key in (10, 13, curses.KEY_ENTER):
                self._begin_edit()
            return

        if key == 27:
            self._cancel_edit()
        elif key in (10, 13, curses.KEY_ENTER):
            self._commit_edit()
        elif self.focus == 0:
            self._edit_frequency(key)
        elif key == curses.KEY_UP:
            self.menu_index = (self.menu_index - 1) % len(self._choices())
        elif key == curses.KEY_DOWN:
            self.menu_index = (self.menu_index + 1) % len(self._choices())

    def _begin_edit(self) -> None:
        self.editing = True
        if self.focus == 0:
            self.frequency_digits = frequency_to_digits(self.settings.frequency_mhz)
            self.digit_index = 0
            return
        current = self._field_value(self.focus)
        choices = self._choices()
        self.menu_index = choices.index(current)

    def _cancel_edit(self) -> None:
        self.editing = False
        self.retune_at = None
        self.frequency_digits = frequency_to_digits(self.settings.frequency_mhz)
        self.message = "Edit cancelled"

    def _edit_frequency(self, key: int) -> None:
        digits = list(self.frequency_digits)
        if ord("0") <= key <= ord("9"):
            digits[self.digit_index] = chr(key)
            self.digit_index = min(6, self.digit_index + 1)
        elif key == curses.KEY_LEFT:
            self.digit_index = max(0, self.digit_index - 1)
            return
        elif key == curses.KEY_RIGHT:
            self.digit_index = min(6, self.digit_index + 1)
            return
        elif key == curses.KEY_UP:
            digits[self.digit_index] = str((int(digits[self.digit_index]) + 1) % 10)
        elif key == curses.KEY_DOWN:
            digits[self.digit_index] = str((int(digits[self.digit_index]) - 1) % 10)
        else:
            return
        self.frequency_digits = "".join(digits)
        if self.pipeline.playing:
            self.retune_at = time.monotonic() + 0.5
            self.message = "Retune pending…"

    def _frequency_candidate(self) -> ReceiverSettings:
        value = digits_to_frequency(self.frequency_digits)
        return replace(self.settings, frequency_mhz=value).validated()

    def _handle_pending_retune(self) -> None:
        if self.retune_at is None or time.monotonic() < self.retune_at:
            return
        self.retune_at = None
        try:
            candidate = self._frequency_candidate()
        except ValueError as exc:
            self.message = str(exc)
            return
        self.settings = candidate
        try:
            self.pipeline.apply(candidate)
        except RuntimeError as exc:
            self.message = str(exc)

    def _commit_edit(self) -> None:
        try:
            if self.focus == 0:
                candidate = self._frequency_candidate()
            else:
                choice = self._choices()[self.menu_index]
                if self.focus == 1:
                    candidate = self.settings.with_mode(choice)
                elif self.focus == 2:
                    candidate = replace(self.settings, bandwidth=choice)
                else:
                    candidate = replace(self.settings, gain=choice)
                candidate = candidate.validated()
        except ValueError as exc:
            self.message = str(exc)
            return
        self.settings = candidate
        self.frequency_digits = frequency_to_digits(candidate.frequency_mhz)
        self.retune_at = None
        self.editing = False
        try:
            self.pipeline.apply(candidate)
            self.message = f"{FIELDS[self.focus]} committed"
        except RuntimeError as exc:
            self.message = str(exc)

    def _change_volume(self, amount: int) -> None:
        volume = min(100, max(0, self.settings.volume + amount))
        self.settings = replace(self.settings, volume=volume)
        self.pipeline.apply(self.settings, restart=False)
        self.message = f"Volume {volume}%"

    def _toggle_play(self) -> None:
        try:
            if self.pipeline.playing:
                self.pipeline.stop()
            else:
                self.pipeline.apply(self.settings, restart=False)
                self.pipeline.start()
        except (OSError, RuntimeError) as exc:
            self.message = f"Cannot play: {exc}"


def run_ui(pipeline: ReceiverPipeline, autoplay: bool = False) -> None:
    curses.wrapper(lambda screen: PocketReceiverUI(screen, pipeline, autoplay).run())
