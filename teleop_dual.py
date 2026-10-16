#!/usr/bin/env python3
# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Independent threaded dual-arm teleoperation entrypoint."""

import sys

from teleop_app import teleop_dual as _teleop_dual


if __name__ == "__main__":
    _teleop_dual.main()
else:
    sys.modules[__name__] = _teleop_dual
