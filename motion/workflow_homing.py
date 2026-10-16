# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Minimum-jerk return-to-zero planner for the teleop workflow.

This standalone planner interpolates any number of follower arms to zero.
It owns no state machine, logging, threads, ROS calls, or hardware access.
The quintic time law has zero velocity and acceleration at both ends.
Duration follows true peak speed and acceleration limits with a minimum floor.
"""

import math

import numpy as np

# Return trajectory timing constants.
HOME_SPEED_RAD_S = 2.0     # Peak angular speed (rad/s).
HOME_ACCEL_RAD_S2 = 4.0    # Peak angular acceleration (rad/s²).
HOME_MIN_DURATION_S = 0.5  # Minimum duration (s).

# Peak derivatives of alpha(t)=10t³-15t⁴+6t⁵ on [0, 1].
# The old travel/speed duration underestimated peak speed by 15/8.
_MIN_JERK_PEAK_VEL = 15.0 / 8.0
_MIN_JERK_PEAK_ACC = 10.0 * math.sqrt(3.0) / 3.0


class HomingPlanner:
    """Minimum-jerk return trajectory for any number of arms.

    Call from the control loop:
        planner.begin(get_follower_pos(), now)     # Capture starting poses.
        while planner.active:
            done, cmd = planner.step(now)          # One control cycle.
            command_follower(cmd)                  # Send follower targets.
            if done: break                         # Zero reached.
    """

    def __init__(self, *, speed_rad_s: float = HOME_SPEED_RAD_S,
                 accel_rad_s2: float = HOME_ACCEL_RAD_S2,
                 min_duration_s: float = HOME_MIN_DURATION_S):
        for name, value in (
            ("speed_rad_s", speed_rad_s),
            ("accel_rad_s2", accel_rad_s2),
            ("min_duration_s", min_duration_s),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        self._speed = speed_rad_s
        self._accel = accel_rad_s2
        self._min_dur = min_duration_s
        self._start = None          # Starting poses; None when inactive.
        self._t0 = 0.0
        self._dur = min_duration_s

    @property
    def active(self) -> bool:
        """Whether return interpolation is active."""
        return self._start is not None

    @property
    def duration(self) -> float:
        """Current return duration in seconds."""
        return self._dur

    def begin(self, pos_list, now: float) -> float:
        """Capture starts, calculate duration, and begin returning to zero."""
        self._start = [np.asarray(p, float).copy() for p in pos_list]
        if not self._start or any(
            p.size == 0 or not np.all(np.isfinite(p)) for p in self._start
        ):
            self._start = None
            raise ValueError("return starts must be nonempty finite arrays")
        max_travel = max(float(np.max(np.abs(p))) for p in self._start)
        velocity_duration = _MIN_JERK_PEAK_VEL * max_travel / self._speed
        acceleration_duration = math.sqrt(
            _MIN_JERK_PEAK_ACC * max_travel / self._accel
        )
        self._dur = max(
            self._min_dur, velocity_duration, acceleration_duration
        )
        self._t0 = now
        return self._dur

    def step(self, now: float):
        """Advance one cycle and return ``(done, cmd_list)``.

        A completed frame contains zeros and deactivates the planner.
        Return ``(False, None)`` when inactive.
        """
        if self._start is None:
            return False, None
        t = (now - self._t0) / self._dur
        if t >= 1.0:
            cmd = [np.zeros_like(p) for p in self._start]
            self._start = None
            return True, cmd
        alpha = 10 * t**3 - 15 * t**4 + 6 * t**5   # minimum jerk
        return False, [p * (1.0 - alpha) for p in self._start]
