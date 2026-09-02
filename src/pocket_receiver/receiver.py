"""Robust rtl_fm -> volume scaler -> ALSA process pipeline."""

from __future__ import annotations

import array
import os
import shutil
import signal
import subprocess
import sys
import threading
from collections import deque
from collections.abc import Callable

from .model import ReceiverSettings, bandwidth_hz
from .lease import ReadsbLease


class ReceiverPipeline:
    """Own, monitor, terminate and reap both receiver child processes."""

    def __init__(
        self,
        settings: ReceiverSettings,
        device: int = 0,
        audio_device: str = "default",
        report: Callable[[str], None] | None = None,
        lease: ReadsbLease | None = None,
    ):
        self.settings = settings.validated()
        self.device = device
        self.audio_device = audio_device
        self.report = report or (lambda _message: None)
        self.lease = lease
        self._rtl: subprocess.Popen[bytes] | None = None
        self._aplay: subprocess.Popen[bytes] | None = None
        self._threads: list[threading.Thread] = []
        self._stopping = threading.Event()
        self._lock = threading.RLock()
        self._errors: deque[str] = deque(maxlen=8)

    @property
    def playing(self) -> bool:
        with self._lock:
            return bool(
                self._rtl
                and self._aplay
                and self._rtl.poll() is None
                and self._aplay.poll() is None
            )

    @property
    def last_error(self) -> str:
        return self._errors[-1] if self._errors else ""

    def _rtl_command(self) -> list[str]:
        s = self.settings
        command = [
            "rtl_fm",
            "-d", str(self.device),
            "-f", str(round(s.frequency_mhz * 1_000_000)),
            "-M", s.mode.lower(),
            "-s", str(bandwidth_hz(s.bandwidth)),
            "-r", "48000",
        ]
        if s.gain != "Auto":
            command += ["-g", s.gain]
        if s.mode == "WFM":
            command += ["-E", "deemp"]
        command.append("-")
        return command

    def _aplay_command(self) -> list[str]:
        return [
            "aplay", "-q", "-D", self.audio_device,
            "-r", "48000", "-f", "S16_LE", "-c", "1",
        ]

    def check_dependencies(self) -> None:
        missing = [name for name in ("rtl_fm", "aplay") if shutil.which(name) is None]
        if missing:
            raise RuntimeError("Missing command(s): " + ", ".join(missing))

    def start(self) -> None:
        with self._lock:
            if self.playing:
                return
            self.check_dependencies()
            if self.lease:
                self.lease.acquire()
            self._stopping.clear()
            self._errors.clear()
            try:
                self._rtl = subprocess.Popen(
                    self._rtl_command(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    start_new_session=True,
                )
                self._aplay = subprocess.Popen(
                    self._aplay_command(), stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                    start_new_session=True,
                )
            except Exception:
                self._terminate_children()
                if self.lease:
                    self.lease.release()
                raise

            self._threads = [
                threading.Thread(target=self._pump_audio, name="audio-pump", daemon=True),
                threading.Thread(target=self._read_errors, args=(self._rtl, "RTL-SDR"), daemon=True),
                threading.Thread(target=self._read_errors, args=(self._aplay, "Audio"), daemon=True),
                threading.Thread(target=self._monitor, name="receiver-monitor", daemon=True),
            ]
            for thread in self._threads:
                thread.start()
            self.report(
                f"Playing {self.settings.frequency_mhz:.3f} MHz {self.settings.mode}"
            )

    def _pump_audio(self) -> None:
        rtl = self._rtl
        aplay = self._aplay
        if not rtl or not rtl.stdout or not aplay or not aplay.stdin:
            return
        try:
            while not self._stopping.is_set():
                chunk = rtl.stdout.read(8192)
                if not chunk:
                    break
                if len(chunk) % 2:
                    chunk = chunk[:-1]
                samples = array.array("h")
                samples.frombytes(chunk)
                if sys.byteorder != "little":
                    samples.byteswap()
                scale = self.settings.volume / 100.0
                if scale != 1.0:
                    for index, value in enumerate(samples):
                        samples[index] = round(value * scale)
                if sys.byteorder != "little":
                    samples.byteswap()
                aplay.stdin.write(samples.tobytes())
                aplay.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass
        finally:
            try:
                aplay.stdin.close()
            except OSError:
                pass

    def _read_errors(self, process: subprocess.Popen[bytes], label: str) -> None:
        if not process.stderr:
            return
        for raw_line in iter(process.stderr.readline, b""):
            line = raw_line.decode(errors="replace").strip()
            if not line:
                continue
            # rtl_fm prints normal setup chatter to stderr. Keep it available, but
            # surface the messages most likely to explain a failed start.
            lowered = line.lower()
            if (
                any(word in lowered for word in ("error", "failed", "busy", "permission denied"))
                or "no supported devices found" in lowered
            ):
                message = f"{label}: {line}"
                self._errors.append(message)
                self.report(message)

    def _monitor(self) -> None:
        rtl = self._rtl
        aplay = self._aplay
        if not rtl or not aplay:
            return
        while not self._stopping.is_set():
            rtl_code = rtl.poll()
            audio_code = aplay.poll()
            if rtl_code is not None or audio_code is not None:
                failed_name = "rtl_fm" if rtl_code is not None else "aplay"
                failed_code = rtl_code if rtl_code is not None else audio_code
                detail = self.last_error or f"{failed_name} exited with status {failed_code}"
                self.report(f"Receiver stopped: {detail}")
                self._stopping.set()
                break
            self._stopping.wait(0.05)
        self._terminate(rtl)
        self._terminate(aplay)
        rtl.wait()
        aplay.wait()

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes] | None) -> None:
        if not process or process.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            process.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=1.5)
        except ProcessLookupError:
            pass

    def _terminate_children(self) -> None:
        self._terminate(self._rtl)
        self._terminate(self._aplay)

    def stop(self) -> None:
        with self._lock:
            was_running = bool(self._rtl or self._aplay)
            self._stopping.set()
            self._terminate_children()
            for process in (self._rtl, self._aplay):
                if process:
                    try:
                        process.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        self._terminate(process)
            current = threading.current_thread()
            for thread in self._threads:
                if thread is not current and thread.is_alive():
                    thread.join(timeout=0.25)
            self._rtl = None
            self._aplay = None
            if was_running:
                self.report("Paused")

    def apply(self, settings: ReceiverSettings, restart: bool = True) -> None:
        settings = settings.validated()
        with self._lock:
            was_playing = self.playing
            volume_only = (
                settings.frequency_mhz == self.settings.frequency_mhz
                and settings.mode == self.settings.mode
                and settings.bandwidth == self.settings.bandwidth
                and settings.gain == self.settings.gain
            )
            self.settings = settings
        if was_playing and restart and not volume_only:
            self.stop()
            self.start()

    def close(self) -> None:
        self.stop()
        if self.lease:
            self.lease.release()
