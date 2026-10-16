# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

"""Configuration loading for the teleoperation application."""

from pathlib import Path

import yaml


_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_config(path=None) -> dict:
    """Load teleop settings and resolve the selected A1Z-T hardware profile."""
    p = Path(path) if path else _CONFIG_PATH
    with open(p, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("Teleop config must be a YAML mapping")
    version = config.get("a1z_t_version")
    if version not in ("EVT", "PVT"):
        raise ValueError(f"Invalid a1z_t_version {version!r}; choose EVT or PVT")
    profiles = config.pop("a1z_t_profiles", None)
    if not isinstance(profiles, dict) or not isinstance(profiles.get(version), dict):
        raise ValueError(f"Missing A1Z-T profile for {version}")
    profile = profiles[version]
    if "trigger_limit" not in profile or "a1z_t_joint_signs" not in profile:
        raise ValueError(f"Incomplete A1Z-T profile for {version}")
    config["trigger_limit"] = profile["trigger_limit"]
    config["a1z_t_joint_signs"] = profile["a1z_t_joint_signs"]
    return config
