# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Motion planning utilities independent of the arm hardware."""

from .homing import (
    HOME_ACCEL_RAD_S2,
    HOME_MIN_DURATION_S,
    HOME_SPEED_RAD_S,
    HomingPlanner,
)
from .joint_trajectory import JointTrajectoryPoint, MinimumJerkTrajectory
from .startup_homing import home_robots

__all__ = [
    "HOME_ACCEL_RAD_S2",
    "HOME_MIN_DURATION_S",
    "HOME_SPEED_RAD_S",
    "HomingPlanner",
    "JointTrajectoryPoint",
    "MinimumJerkTrajectory",
    "home_robots",
]
