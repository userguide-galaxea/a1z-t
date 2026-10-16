# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Joint-space minimum-jerk trajectory with speed and acceleration limits."""

from dataclasses import dataclass
import math

import numpy as np

MINIMUM_JERK_PEAK_VELOCITY = 15.0 / 8.0
MINIMUM_JERK_PEAK_ACCELERATION = 10.0 * math.sqrt(3.0) / 3.0


@dataclass(frozen=True)
class JointTrajectoryPoint:
    """A joint trajectory sample at one instant."""

    position: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray
    done: bool


class MinimumJerkTrajectory:
    """Quintic trajectory from any start to any target."""

    def __init__(self, start, target, *, max_velocity: float,
                 max_acceleration: float, min_duration: float,
                 start_time: float, duration: "float | None" = None):
        start_array = np.asarray(start, dtype=float)
        target_array = np.asarray(target, dtype=float)
        if start_array.shape != target_array.shape or start_array.ndim != 1:
            raise ValueError("start and target must be 1D joint vectors of equal shape")
        if not np.all(np.isfinite(start_array)) or not np.all(np.isfinite(target_array)):
            raise ValueError("start and target must contain only finite values")
        for name, value in (
            ("max_velocity", max_velocity),
            ("max_acceleration", max_acceleration),
            ("min_duration", min_duration),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not math.isfinite(start_time):
            raise ValueError("start_time must be finite")

        self._start = start_array.copy()
        self._target = target_array.copy()
        self._delta = self._target - self._start
        self._start_time = float(start_time)
        required = self.required_duration(
            self._start, self._target,
            max_velocity=max_velocity,
            max_acceleration=max_acceleration,
            min_duration=min_duration,
        )
        if duration is None:
            self._duration = required
        else:
            if not math.isfinite(duration) or duration < required:
                raise ValueError("duration is shorter than the constrained trajectory")
            self._duration = float(duration)

    @staticmethod
    def required_duration(start, target, *, max_velocity: float,
                          max_acceleration: float,
                          min_duration: float) -> float:
        """Find the shortest duration satisfying peak speed and acceleration."""
        start_array = np.asarray(start, dtype=float)
        target_array = np.asarray(target, dtype=float)
        if start_array.shape != target_array.shape or start_array.ndim != 1:
            raise ValueError("start and target must be 1D joint vectors of equal shape")
        if not np.all(np.isfinite(start_array)) or not np.all(np.isfinite(target_array)):
            raise ValueError("start and target must contain only finite values")
        if max_velocity <= 0 or max_acceleration <= 0 or min_duration <= 0:
            raise ValueError("trajectory limits must be positive")
        travel = float(np.max(np.abs(target_array - start_array), initial=0.0))
        velocity_duration = MINIMUM_JERK_PEAK_VELOCITY * travel / max_velocity
        acceleration_duration = math.sqrt(
            MINIMUM_JERK_PEAK_ACCELERATION * travel / max_acceleration
        )
        return max(float(min_duration), velocity_duration, acceleration_duration)

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def start_time(self) -> float:
        return self._start_time

    def sample(self, now: float) -> JointTrajectoryPoint:
        """Sample at monotonic time; return the exact target after completion."""
        if not math.isfinite(now):
            raise ValueError("now must be finite")
        elapsed = float(now) - self._start_time
        if elapsed >= self._duration:
            zeros = np.zeros_like(self._target)
            return JointTrajectoryPoint(
                self._target.copy(), zeros.copy(), zeros.copy(), True)

        u = float(np.clip(elapsed / self._duration, 0.0, 1.0))
        scale = 10.0 * u**3 - 15.0 * u**4 + 6.0 * u**5
        scale_velocity = (
            30.0 * u**2 - 60.0 * u**3 + 30.0 * u**4
        ) / self._duration
        scale_acceleration = (
            60.0 * u - 180.0 * u**2 + 120.0 * u**3
        ) / self._duration**2
        return JointTrajectoryPoint(
            (self._start + self._delta * scale).copy(),
            (self._delta * scale_velocity).copy(),
            (self._delta * scale_acceleration).copy(),
            False,
        )
