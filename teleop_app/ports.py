# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Resolve Follower CAN interface names for teleoperation and tools."""

import os
import sys
from collections.abc import Callable


def default_can(
    side: str, *, exists: Callable[[str], bool] = os.path.exists
) -> str:
    if side not in ("left", "right"):
        raise ValueError(f"unknown CAN side: {side}")
    index = 0 if side == "left" else 1
    preferred = f"can_{side}"
    if exists(f"/sys/class/net/{preferred}"):
        return preferred
    legacy = f"can{index}"
    print(f"[WARN] {preferred} is missing; using legacy CAN interface {legacy}", file=sys.stderr)
    return legacy
