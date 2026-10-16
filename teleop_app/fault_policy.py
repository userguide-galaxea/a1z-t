# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Leader communication fault policy for teleoperation.

This module intentionally has no ROS or hardware dependencies so the timing
policy can be unit-tested offline. Hardware actions (short hold, latched MIT
hold, and recovery) remain the responsibility of the caller.
"""

import enum
import threading
from dataclasses import dataclass
from typing import Optional, Tuple


class LeaderFaultState(enum.Enum):
    """Leader input health as seen by the teleoperation control loop."""

    OK = "OK"
    HOLD = "HOLD"
    LATCHED_HOLD = "LATCHED_HOLD"


@dataclass(frozen=True)
class LeaderFaultDecision:
    """Action requested after one complete dual-Leader read attempt."""

    state: LeaderFaultState
    hold_last: bool = False
    enter_latched_hold: bool = False
    resumed_from_hold: bool = False


class LeaderFaultPolicy:
    """Escalate a short Leader read loss from HOLD to a latched MIT hold.

    A failure means that a complete left+right Leader sample was not obtained.
    Any successful complete sample clears a short HOLD. Once the latch
    threshold is crossed, communication recovery is only observed; it never
    automatically releases the latch.  The caller must explicitly request and
    perform recovery after ``recovery_stable_s`` of healthy samples.
    """

    def __init__(
        self,
        latch_after_s: float = 0.25,
        recovery_stable_s: float = 0.50,
        max_success_gap_s: float = 0.05,
        min_recovery_samples: int = 10,
    ) -> None:
        if latch_after_s <= 0:
            raise ValueError("latch_after_s must be > 0")
        if recovery_stable_s < 0:
            raise ValueError("recovery_stable_s must be >= 0")
        if max_success_gap_s <= 0:
            raise ValueError("max_success_gap_s must be > 0")
        if min_recovery_samples < 1:
            raise ValueError("min_recovery_samples must be >= 1")
        self._latch_after_s = float(latch_after_s)
        self._recovery_stable_s = float(recovery_stable_s)
        self._max_success_gap_s = float(max_success_gap_s)
        self._min_recovery_samples = int(min_recovery_samples)
        self._state = LeaderFaultState.OK
        self._fault_since: Optional[float] = None
        self._healthy_since: Optional[float] = None
        self._last_success_at: Optional[float] = None
        self._consecutive_successes = 0
        self._last_error = ""
        self._lock = threading.Lock()

    @property
    def state(self) -> LeaderFaultState:
        with self._lock:
            return self._state

    @property
    def last_error(self) -> str:
        with self._lock:
            return self._last_error

    def on_failure(
        self,
        now: float,
        detail: str,
        fault_started_at: Optional[float] = None,
    ) -> LeaderFaultDecision:
        """Record one incomplete dual-Leader sample."""
        with self._lock:
            self._last_error = detail
            self._healthy_since = None
            self._last_success_at = None
            self._consecutive_successes = 0
            if self._state == LeaderFaultState.OK:
                self._state = LeaderFaultState.HOLD
                self._fault_since = (
                    min(now, fault_started_at)
                    if fault_started_at is not None
                    else now
                )

            enter_latched_hold = False
            if (
                self._state == LeaderFaultState.HOLD
                and self._fault_since is not None
                and now - self._fault_since >= self._latch_after_s
            ):
                self._state = LeaderFaultState.LATCHED_HOLD
                enter_latched_hold = True

            return LeaderFaultDecision(
                state=self._state,
                hold_last=True,
                enter_latched_hold=enter_latched_hold,
            )

    def on_success(self, now: float) -> LeaderFaultDecision:
        """Record one complete, valid left+right Leader sample."""
        with self._lock:
            if self._state == LeaderFaultState.HOLD:
                self._state = LeaderFaultState.OK
                self._fault_since = None
                self._healthy_since = None
                self._last_success_at = None
                self._consecutive_successes = 0
                self._last_error = ""
                return LeaderFaultDecision(
                    state=self._state,
                    resumed_from_hold=True,
                )

            if self._state == LeaderFaultState.LATCHED_HOLD:
                gap = (
                    now - self._last_success_at
                    if self._last_success_at is not None
                    else None
                )
                if (
                    self._healthy_since is None
                    or gap is None
                    or gap > self._max_success_gap_s
                ):
                    self._healthy_since = now
                    self._consecutive_successes = 1
                else:
                    self._consecutive_successes += 1
                self._last_success_at = now
                return LeaderFaultDecision(state=self._state)

            return LeaderFaultDecision(state=self._state)

    def can_recover(self, now: float) -> Tuple[bool, str]:
        """Return whether an explicit recovery request may be accepted."""
        with self._lock:
            if self._state != LeaderFaultState.LATCHED_HOLD:
                return False, "No Leader communication fault is latched"
            if self._healthy_since is None:
                return False, "Leader communication has not recovered on both sides"
            if (
                self._last_success_at is None
                or now - self._last_success_at > self._max_success_gap_s
            ):
                return False, "Leader healthy samples timed out; wait for continuous feedback"
            if self._consecutive_successes < self._min_recovery_samples:
                return (
                    False,
                    f"Insufficient consecutive healthy Leader samples "
                    f"({self._consecutive_successes}/{self._min_recovery_samples})",
                )
            healthy_for = now - self._healthy_since
            if healthy_for < self._recovery_stable_s:
                remaining = self._recovery_stable_s - healthy_for
                return False, f"Leader communication must remain stable for {remaining:.2f}s more"
            return True, ""

    def mark_recovered(self, now: float) -> None:
        """Clear the latch after the caller has safely reset both bridges."""
        del now  # kept in the signature so callers use the same monotonic clock
        with self._lock:
            if self._state != LeaderFaultState.LATCHED_HOLD:
                raise RuntimeError("Leader fault is not latched")
            self._state = LeaderFaultState.OK
            self._fault_since = None
            self._healthy_since = None
            self._last_success_at = None
            self._consecutive_successes = 0
            self._last_error = ""
