# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""JoyCon-driven teleoperation workflow state machine.

    HOME --button--> READY --button--> HOMING --at zero--> HOME

HOME holds the Follower and Leader at zero. READY follows Leader input.
HOMING returns the Follower by minimum-jerk interpolation and drives the
Leader home with a limited profile; button presses are ignored until done.
Hardware actions arrive through callbacks. Call all methods from the control
loop thread so workflow and bridge share one CAN writer.
"""

import enum
import threading
import time

from motion.workflow_homing import HomingPlanner
from a1z_t.joycon import BUTTON_MISS_LIMIT, ButtonStateTracker, ButtonToggle


class TeleopState(enum.Enum):
    HOME = "HOME"        # Arms at zero, teleoperation paused.
    READY = "READY"      # Leader following active.
    HOMING = "HOMING"    # Returning to zero.


class TeleopWorkflow:
    """Main teleop state machine with injected hardware callbacks.

    ``set_teleop_enabled`` toggles bridge following; ``reset_bridges``
    captures fresh zero points. Leader callbacks hold, release, or home the
    Leader; Follower callbacks read and command arm positions. Initially,
    HOME pauses teleoperation and holds the Leader at zero.
    """

    def __init__(self, *, set_teleop_enabled, reset_bridges,
                 lock_leaders, release_leaders,
                 get_follower_pos, command_follower, log=print,
                 home_leaders=None):
        self._set_teleop_enabled = set_teleop_enabled
        self._reset_bridges = reset_bridges
        self._lock_leaders = lock_leaders
        self._release_leaders = release_leaders
        self._get_follower_pos = get_follower_pos
        self._command_follower = command_follower
        self._log = log
        self._home_leaders = (
            home_leaders if home_leaders is not None else lock_leaders
        )

        self._lock = threading.Lock()
        self._state = TeleopState.HOME

        # Use a minimum-jerk planner for the return trajectory.
        self._homing = HomingPlanner()

        # Enter HOME with teleoperation paused and the Leader held.
        self._set_teleop_enabled(False)
        self._lock_leaders()

    # State access.

    @property
    def state(self) -> TeleopState:
        with self._lock:
            return self._state

    def _goto(self, new: TeleopState, msg: str = "") -> None:
        self._state = new
        if msg:
            self._log(msg)

    def control_mode(self) -> str:
        """Return TELEOP, HOMING, or IDLE for the current control frame."""
        with self._lock:
            s = self._state
        if s == TeleopState.READY:
            return "TELEOP"
        if s == TeleopState.HOMING:
            return "HOMING"
        return "IDLE"   # HOME

    # Button events.

    def on_toggle(self) -> None:
        """Handle a button edge: start, return home, or ignore during homing."""
        with self._lock:
            s = self._state
            if s == TeleopState.HOME:
                self._start_teleop()
            elif s == TeleopState.READY:
                self._begin_homing()
            else:
                self._log("Button ignored: homing in progress; wait until zero is reached")

    # State transitions, called while holding the lock.

    def _start_teleop(self) -> None:
        self._release_leaders()
        self._reset_bridges()
        self._set_teleop_enabled(True)
        self._goto(TeleopState.READY, "▶ Teleoperation started (HOME → READY); press again to return home")

    def _begin_homing(self) -> None:
        self._set_teleop_enabled(False)
        try:
            dur = self._homing.begin(
                self._get_follower_pos(), time.monotonic()
            )
        except (RuntimeError, ValueError) as exc:
            self._log(
                f"! Return to zero refused: {exc}; Follower is held. Restore feedback, then press again"
            )
            return
        self._home_leaders()
        self._goto(TeleopState.HOMING,
                   f"⟲ Follower returning to zero (~{dur:.1f}s); Leader homing/held")

    # Control-loop progression.

    def step_homing(self, now: float) -> None:
        """Advance HOMING once per cycle on the bridge/CAN writer thread.
        """
        with self._lock:
            if self._state != TeleopState.HOMING or not self._homing.active:
                return
            done, cmd = self._homing.step(now)
            self._command_follower(cmd)
            if done:
                self._goto(TeleopState.HOME,
                           "✓ Zero reached (→ HOME); press to restart teleoperation, Ctrl+C to exit")
