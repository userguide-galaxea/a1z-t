"""Check hardware profile selection without accessing any devices."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from teleop_app import config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.checkout = self.root / "config.yaml"
        self.packaged = self.root / "teleop_app" / "config.yaml"
        self.packaged.parent.mkdir()
        # Keep the shipped profiles, but select different versions in each file.
        self.settings = yaml.safe_load(config._PACKAGED_CONFIG_PATH.read_text())
        for path, version in ((self.checkout, "PVT"), (self.packaged, "EVT")):
            self.write_config(path, version)
        paths = patch.multiple(config, _CONFIG_PATH=self.checkout,
                               _PACKAGED_CONFIG_PATH=self.packaged)
        paths.start()
        self.addCleanup(paths.stop)

    def write_config(self, path, version):
        settings = dict(self.settings, a1z_t_version=version)
        path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    def test_checkout_pvt_overrides_packaged_evt(self):
        cfg = config.load_config()
        self.assertEqual(cfg["a1z_t_version"], "PVT")
        self.assertEqual(cfg["a1z_t_joint_signs"][2], 1)
        self.assertEqual(cfg["trigger_limit"],
                         self.settings["a1z_t_profiles"]["PVT"]["trigger_limit"])

    def test_normal_install_uses_packaged_fallback(self):
        self.checkout.unlink()
        cfg = config.load_config()
        self.assertEqual(cfg["a1z_t_version"], "EVT")
        self.assertEqual(cfg["a1z_t_joint_signs"][2], -1)

    def test_explicit_path_overrides_checkout(self):
        self.assertEqual(config.load_config(self.packaged)["a1z_t_version"], "EVT")

    def test_invalid_checkout_does_not_silently_use_evt_fallback(self):
        self.write_config(self.checkout, "invalid")
        with self.assertRaisesRegex(ValueError, "Invalid a1z_t_version"):
            config.load_config()


if __name__ == "__main__":
    unittest.main()
