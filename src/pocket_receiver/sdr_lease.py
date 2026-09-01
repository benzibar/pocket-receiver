from __future__ import annotations

import subprocess
import time


class SdrLeaseError(RuntimeError):
    pass


class ReadsbLease:
    def __init__(
        self,
        service: str = "readsb",
        stop_timeout_seconds: float = 2.0,
        start_timeout_seconds: float = 3.0,
    ) -> None:
        self.service = service
        self.stop_timeout_seconds = stop_timeout_seconds
        self.start_timeout_seconds = start_timeout_seconds
        self.restart_needed = False

    def _is_active(self) -> bool:
        return subprocess.run(
            ["systemctl", "is-active", "--quiet", self.service],
            check=False,
        ).returncode == 0

    def _wait_for_state(self, active: bool, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self._is_active() == active:
                return True
            time.sleep(0.1)
        return self._is_active() == active

    def acquire(self) -> None:
        self.restart_needed = self._is_active()
        if not self.restart_needed:
            return

        result = subprocess.run(
            ["sudo", "-n", "systemctl", "stop", self.service],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self.restart_needed = False
            msg = (result.stderr or result.stdout).strip()
            raise SdrLeaseError(msg or "Could not stop readsb.")

        if not self._wait_for_state(False, self.stop_timeout_seconds):
            self.restart_needed = False
            raise SdrLeaseError("readsb did not stop in time.")

    def release(self) -> None:
        if not self.restart_needed:
            return
        try:
            result = subprocess.run(
                ["sudo", "-n", "systemctl", "start", self.service],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                msg = (result.stderr or result.stdout).strip()
                raise SdrLeaseError(msg or "Could not restart readsb.")
            if not self._wait_for_state(True, self.start_timeout_seconds):
                raise SdrLeaseError("readsb did not restart in time.")
        finally:
            self.restart_needed = False
