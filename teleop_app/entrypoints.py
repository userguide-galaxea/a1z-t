# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Pass a public teleop entrypoint's arguments to the shared control loop."""

import sys

from teleop_app import teleop_runtime


def run(mode: str, argv=None):
    if argv is None:
        return teleop_runtime.main(mode=mode)

    original_argv = sys.argv
    sys.argv = [f"teleop_{mode}.py", *argv]
    try:
        return teleop_runtime.main(mode=mode)
    finally:
        sys.argv = original_argv
