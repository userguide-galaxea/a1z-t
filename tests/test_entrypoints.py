"""Exercise the distributed runtime without opening serial ports or CAN."""

import contextlib
import io
import sys
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from teleop_app import entrypoints


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.runtime = entrypoints.teleop_runtime
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(vars(self.runtime)))
        vars(self.runtime).pop("_sync", None)
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.stack.enter_context(contextlib.redirect_stderr(io.StringIO()))

    def mock_hardware(self, *, dual=False, joycon=False):
        reader, robot = MagicMock(), MagicMock()
        hardware = (reader, MagicMock() if dual else None,
                    robot, MagicMock() if dual else None, None, None)
        self.stack.enter_context(patch.object(
            self.runtime, "_initialize_teleop_hardware", return_value=hardware))
        self.stack.enter_context(patch.object(self.runtime, "_wait_leaders_at_zero"))
        self.cleanup = self.stack.enter_context(patch.object(
            self.runtime, "_cleanup_teleop_hardware"))
        self.stack.enter_context(patch.object(self.runtime, "TeleopBridge"))
        self.stack.enter_context(patch.object(
            self.runtime, "_read_joycon_state", return_value=object() if joycon else None))
        self.stack.enter_context(patch.object(
            self.runtime, "_get_follower_faults", return_value=[]))
        self.stack.enter_context(patch.object(
            self.runtime.select, "select", return_value=([], [], [])))
        self.stack.enter_context(patch("builtins.input", return_value=""))
        self.stack.enter_context(patch.object(sys, "argv", ["test"]))
        self.stack.enter_context(patch.object(sys, "setswitchinterval"))
        return reader, robot

    def single_frame(self, *, recorder=None, joycon=False, public=True):
        self.mock_hardware(joycon=joycon)
        self.left = (np.zeros(6), 0.0, np.zeros(7))
        read = self.stack.enter_context(patch.object(
            self.runtime, "_read_teleop_input_frame",
            side_effect=[(self.left, None, None, {}), KeyboardInterrupt()]))
        dispatch = self.stack.enter_context(patch.object(
            self.runtime, "_dispatch_bridge_frame"))
        argv = ["--port", "/dev/mock-leader", "--can", "mock-can"]
        if public:
            original_main = self.runtime.main
            with patch.object(self.runtime, "main", side_effect=lambda **kw:
                              original_main(trace_recorder=recorder, **kw)):
                entrypoints.run("single", argv)
        else:
            with patch.object(sys, "argv", ["test", *argv]):
                self.runtime.main(mode="single")
        return read, dispatch

    def test_original_runtime_reproduces_missing_sync(self):
        with self.assertRaisesRegex(NameError, "_sync"):
            self.single_frame(public=False)
        self.cleanup.assert_called_once()

    def test_single_arm_processes_frame_and_cleans_up(self):
        read, dispatch = self.single_frame()
        self.assertEqual(read.call_count, 2)
        dispatch.assert_called_once()
        self.assertIs(dispatch.call_args.args[2], self.left)
        self.assertIsNone(dispatch.call_args.args[3])
        self.cleanup.assert_called_once()

    def test_joycon_trace_keeps_right_input_absent(self):
        recorder = MagicMock()
        self.single_frame(recorder=recorder, joycon=True)
        recorder.capture.assert_called_once()
        self.assertIs(recorder.capture.call_args.kwargs["leader_left"], self.left)
        self.assertIsNone(recorder.capture.call_args.kwargs["leader_right"])
        self.cleanup.assert_called_once()

    def test_dual_arm_still_uses_independent_loop(self):
        self.mock_hardware(dual=True)
        independent = self.stack.enter_context(patch.object(
            self.runtime, "_run_independent_teleop"))
        entrypoints.run("dual", [
            "--port", "/dev/mock-left", "--port_right", "/dev/mock-right",
            "--can", "mock-can-left", "--can_right", "mock-can-right"])
        independent.assert_called_once()
        self.cleanup.assert_called_once()


if __name__ == "__main__":
    unittest.main()
