# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Synchronized slow joint-space homing after Follower startup."""

import logging
import math
import time

import numpy as np

from .homing import (
    HOME_ACCEL_RAD_S2,
    HOME_MIN_DURATION_S,
    HOME_SPEED_RAD_S,
    HomingPlanner,
)

logger = logging.getLogger(__name__)

# Coarse final-position check, well above steady gravity error and feedback
# noise. It catches an arm that never moved (estop, rejected commands, bad start).
DEFAULT_GROSS_ERROR_RAD = 0.35


def home_robots(robots, *, targets=None,
                max_velocity: float = HOME_SPEED_RAD_S,
                max_acceleration: float = HOME_ACCEL_RAD_S2,
                min_duration: float = HOME_MIN_DURATION_S,
                control_hz: float,
                gross_error_rad: float = DEFAULT_GROSS_ERROR_RAD,
                clock=time.monotonic, sleep=time.sleep) -> float:
    """Home from measured positions to targets (zero by default).

    Hold the measured pose on the first command, then send a minimum-jerk
    trajectory with velocity feedforward. Return its duration when complete.
    Do not wait for feedback to settle: gravity error and feedback noise can
    otherwise consume the full timeout. Check final position once without
    blocking, and warn if the residual exceeds ``gross_error_rad``.
    Abort immediately if the SDK rejects any command frame. A ``None`` return
    remains compatible with older SDKs and test doubles.
    """
    robot_list = list(robots)
    if not robot_list:
        raise ValueError("At least one initialized arm is required")
    if not math.isfinite(control_hz) or control_hz <= 0:
        raise ValueError("control_hz must be finite and positive")

    starts = [np.asarray(robot.get_joint_pos(), dtype=float)[:6].copy()
              for robot in robot_list]
    goals = ([np.zeros_like(start) for start in starts] if targets is None else
             [np.asarray(target, dtype=float)[:6].copy() for target in targets])
    if len(goals) != len(starts):
        raise ValueError("targets must match the number of robots")

    start_time = float(clock())
    planner = HomingPlanner(
        max_velocity=max_velocity,
        max_acceleration=max_acceleration,
        min_duration=min_duration,
    )
    duration = planner.begin(starts, start_time, targets=goals)
    period = 1.0 / float(control_hz)

    # Use the captured start time; another clock read would move the first frame.
    for index, (robot, start) in enumerate(zip(robot_list, starts)):
        _command_or_raise(
            robot,
            {"pos": start.copy(), "vel": np.zeros_like(start)},
            arm_index=index,
            phase="start hold",
        )

    while True:
        iteration_start = float(clock())
        done, points = planner.step_points(iteration_start)
        if points is None:          # Defensive: begin() must precede the loop.
            break
        for index, (robot, point) in enumerate(zip(robot_list, points)):
            _command_or_raise(
                robot,
                {"pos": point.position, "vel": point.velocity},
                arm_index=index,
                phase="homing trajectory",
            )
        if done:
            break
        elapsed = float(clock()) - iteration_start
        sleep(max(0.0, period - elapsed))

    # Send the exact final pose again with zero velocity.
    for index, (robot, goal) in enumerate(zip(robot_list, goals)):
        _command_or_raise(
            robot,
            {"pos": goal.copy(), "vel": np.zeros_like(goal)},
            arm_index=index,
            phase="final hold",
        )

    _warn_if_not_homed(robot_list, goals, gross_error_rad)
    return duration


def _command_or_raise(robot, command, *, arm_index: int, phase: str) -> None:
    """Send a homing frame and abort startup if the SDK rejects it."""
    accepted = robot.command_joint_state(command)
    if accepted is False:
        position = np.asarray(command["pos"], dtype=float)[:6]
        raise RuntimeError(
            f"arm{arm_index} {phase} command rejected by SDK: "
            f"pos={np.round(position, 3).tolist()} rad; "
            "check joint limits, estop, and command field logs"
        )


def _warn_if_not_homed(robot_list, goals, gross_error_rad: float) -> None:
    """Check measured position once and warn on large residuals."""
    offenders = []
    for index, (robot, goal) in enumerate(zip(robot_list, goals)):
        measured = np.asarray(robot.get_joint_pos(), dtype=float)[:6]
        if not np.all(np.isfinite(measured)):
            offenders.append((index, math.inf, -1))
            continue
        error = np.abs(measured - goal)
        peak = float(np.max(error))
        if peak > gross_error_rad:
            offenders.append((index, peak, int(np.argmax(error))))
    if not offenders:
        return
    logger.warning(
        "Startup homing ended, but measured pose remains far from target "
        "(threshold %.2f rad; possible estop, rejected SDK command, or "
        "invalid start feedback): %s",
        gross_error_rad,
        "; ".join(
            (f"arm{i} joint{j + 1} |Δpos|={p:.3f} rad" if j >= 0
             else f"arm{i} position feedback is non-finite")
            for i, p, j in offenders))
