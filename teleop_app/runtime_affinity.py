# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Parse and apply Linux process and thread CPU affinity."""

from __future__ import annotations

import os


def parse_cpu_affinity(spec: str) -> set[int]:
    """Parse ``2-5,8`` into CPU IDs; an empty value disables pinning."""
    value = str(spec or "").strip()
    if not value:
        return set()

    cpus: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            raise ValueError(f"Invalid CPU affinity format: {spec!r}")
        if "-" in item:
            parts = item.split("-")
            if len(parts) != 2:
                raise ValueError(f"Invalid CPU affinity format: {item!r}")
            start, end = (int(part) for part in parts)
            if start < 0 or end < start:
                raise ValueError(f"Invalid CPU range: {item!r}")
            cpus.update(range(start, end + 1))
        else:
            cpu = int(item)
            if cpu < 0:
                raise ValueError(f"CPU ID cannot be negative: {item!r}")
            cpus.add(cpu)
    return cpus


def apply_process_cpu_affinity(spec: str) -> tuple[int, ...]:
    """Set affinity for this process and future threads; return actual CPUs."""
    requested = parse_cpu_affinity(spec)
    if not requested:
        return ()
    if not hasattr(os, "sched_getaffinity") or not hasattr(os, "sched_setaffinity"):
        raise RuntimeError("CPU affinity is unsupported here; leave cpu_affinity empty")

    allowed = set(os.sched_getaffinity(0))
    unavailable = requested - allowed
    if unavailable:
        raise ValueError(
            f"CPUs {sorted(unavailable)} are outside the process allowance {sorted(allowed)}"
        )
    os.sched_setaffinity(0, requested)
    return tuple(sorted(os.sched_getaffinity(0)))


def apply_thread_cpu_affinity(native_id: int, spec: str) -> tuple[int, ...]:
    """Set affinity for an existing Linux native thread.

    ``threading.Thread.native_id`` is the TID passed to
    ``sched_setaffinity``. This can separate SDK control and Leader I/O.
    """
    requested = parse_cpu_affinity(spec)
    if not requested:
        return ()
    if not hasattr(os, "sched_getaffinity") or not hasattr(os, "sched_setaffinity"):
        raise RuntimeError("CPU affinity is unsupported here; leave cpu_affinity empty")
    tid = int(native_id)
    if tid <= 0:
        raise ValueError(f"Invalid native thread ID: {native_id!r}")
    allowed = set(os.sched_getaffinity(tid))
    unavailable = requested - allowed
    if unavailable:
        raise ValueError(
            f"CPUs {sorted(unavailable)} are outside thread {tid}'s allowance {sorted(allowed)}"
        )
    os.sched_setaffinity(tid, requested)
    return tuple(sorted(os.sched_getaffinity(tid)))
