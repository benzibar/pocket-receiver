"""Cooperative lease of the RTL-SDR from readsb."""

from __future__ import annotations

import subprocess
from collections.abc import Callable


class ReadsbLease:
    """Stop readsb only when it was active, and restore only what we stopped."""

    def __init__(self, enabled: bool = True, report: Callable[[str], None] | None = None):
        self.enabled = enabled
        self.report = report or (lambda _message: None)
        self._stopped_by_us = False

    @staticmethod
    def _run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, text=True, capture_output=True, timeout=10, check=False)

    def acquire(self) -> None:
        if not self.enabled:
            return
        if self._stopped_by_us:
            return
        state = self._run("systemctl", "is-active", "readsb")
        if state.stdout.strip() != "active":
            return
        stopped = self._run("sudo", "-n", "systemctl", "stop", "readsb")
        if stopped.returncode:
            detail = stopped.stderr.strip() or "sudoers may not permit stopping readsb"
            raise RuntimeError(f"Could not lease RTL-SDR from readsb: {detail}")
        self._stopped_by_us = True
        self.report("RTL-SDR leased; readsb paused")

    def release(self) -> None:
        if not self._stopped_by_us:
            return
        started = self._run("sudo", "-n", "systemctl", "start", "readsb")
        self._stopped_by_us = False
        if started.returncode:
            detail = started.stderr.strip() or "unknown systemctl error"
            self.report(f"Warning: could not restore readsb: {detail}")
        else:
            self.report("readsb restored")

    def __enter__(self) -> "ReadsbLease":
        self.acquire()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.release()
