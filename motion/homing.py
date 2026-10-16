# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Joint-space homing for one or more arms on a shared clock."""

import math

import numpy as np

from .joint_trajectory import MinimumJerkTrajectory

HOME_SPEED_RAD_S = 2.0     # Peak speed (rad/s); below the SDK's 4.0 rad/s limit.
HOME_ACCEL_RAD_S2 = 4.0    # Peak acceleration (rad/s²).
HOME_MIN_DURATION_S = 0.5  # Minimum duration (s).


class HomingPlanner:
    """Plan synchronized homing to explicit targets, or zero by default."""

    def __init__(self, *, max_velocity: "float | None" = None,
                 max_acceleration: "float | None" = None,
                 min_duration: "float | None" = None,
                 speed_rad_s: "float | None" = None,
                 min_duration_s: "float | None" = None):
        # The legacy speed_rad_s means travel/duration, not peak speed.
        # New callers should use max_velocity and max_acceleration.
        legacy_timing = speed_rad_s is not None or min_duration_s is not None
        if max_velocity is None:
            max_velocity = (15.0 / 8.0) * (
                HOME_SPEED_RAD_S if speed_rad_s is None else speed_rad_s)
            if not legacy_timing:
                max_velocity = HOME_SPEED_RAD_S
        if max_acceleration is None:
            max_acceleration = 1e12 if legacy_timing else HOME_ACCEL_RAD_S2
        if min_duration is None:
            min_duration = (HOME_MIN_DURATION_S if min_duration_s is None
                            else min_duration_s)
        for name, value in (
            ("max_velocity", max_velocity),
            ("max_acceleration", max_acceleration),
            ("min_duration", min_duration),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        self._max_velocity = float(max_velocity)
        self._max_acceleration = float(max_acceleration)
        self._min_duration = float(min_duration)
        self._trajectories = None
        self._duration = self._min_duration
        self._start_time = 0.0

    @property
    def active(self) -> bool:
        return self._trajectories is not None

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def start_time(self) -> float:
        return self._start_time

    def begin(self, positions, now: float, targets=None) -> float:
        """Capture arm starts and return the synchronized trajectory duration."""
        starts = [np.asarray(position, dtype=float).copy()
                  for position in positions]
        if not starts:
            raise ValueError("At least one arm position is required")
        if targets is None:
            goals = [np.zeros_like(start) for start in starts]
        else:
            goals = [np.asarray(target, dtype=float).copy()
                     for target in targets]
            if len(goals) != len(starts):
                raise ValueError("targets must match the number of positions")
        if not math.isfinite(now):
            raise ValueError("now must be finite")

        durations = []
        for start, goal in zip(starts, goals):
            durations.append(MinimumJerkTrajectory.required_duration(
                start, goal,
                max_velocity=self._max_velocity,
                max_acceleration=self._max_acceleration,
                min_duration=self._min_duration,
            ))
        self._duration = max(durations)
        self._start_time = float(now)
        self._trajectories = [
            MinimumJerkTrajectory(
                start, goal,
                max_velocity=self._max_velocity,
                max_acceleration=self._max_acceleration,
                min_duration=self._min_duration,
                start_time=self._start_time,
                duration=self._duration,
            )
            for start, goal in zip(starts, goals)
        ]
        return self._duration

    def step_points(self, now: float):
        """Return synchronized position, velocity, and acceleration samples."""
        if self._trajectories is None:
            return False, None
        points = [trajectory.sample(now) for trajectory in self._trajectories]
        done = all(point.done for point in points)
        if done:
            self._trajectories = None
        return done, points

    def step(self, now: float):
        """Return ``(done, positions)`` for the workflow compatibility API."""
        done, points = self.step_points(now)
        if points is None:
            return False, None
        return done, [point.position for point in points]

    def cancel(self) -> None:
        self._trajectories = None
