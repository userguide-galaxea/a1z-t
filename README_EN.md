# A1Z-T: A1Z Teleoperation

[简体中文](README.md)

Single-arm and dual-arm teleoperation for A1Z-T and A1Z. Dual-arm mode runs the two arms in independent threads.

## Install

Requires Ubuntu 22.04 and CPython 3.11.

Initialize the submodule from the repository root:

```bash
git submodule update --init GALAXEA-A1Z
```

Choose one environment setup method.

### venv

```bash
python3.11 -m venv --system-site-packages .venv
source .venv/bin/activate
```

### Conda

Install Conda first.

```bash
conda create -n a1z-teleop python=3.11 -y
conda activate a1z-teleop
```

With the chosen environment active, install the project from the repository root:

```bash
python -m pip install -e .
```

## Set up devices

Confirm which serial and CAN interfaces belong to each arm. To assign stable names, list the connected adapters and provide their serial numbers to the setup script:

```bash
bash scripts/setup_ports.sh --list
LEADER_LEFT_SERIAL=... CAN_LEFT_SERIAL=... bash scripts/setup_ports.sh
```

For dual-arm operation, also set `LEADER_RIGHT_SERIAL` and `CAN_RIGHT_SERIAL`. Reconnect the adapters or reboot after installing the rules. Run only the first command for one arm, or both commands for two arms:

```bash
bash scripts/setup_can.sh can_left
bash scripts/setup_can.sh can_right
```

Select `EVT` or `PVT` with `a1z_t_version` in [`config.yaml`](config.yaml) before running.

## Try Teleoperation

```bash
python teleop_single.py --port /dev/leader_left --can can_left

python teleop_dual.py --port /dev/leader_left --port_right /dev/leader_right \
  --can_left can_left --can_right can_right
```

After startup homing, use the control button to start or stop tracking. Press `Ctrl+C` to exit. Use `--help` on either entrypoint for its available options. Dual-arm mode does not bind CPU cores by default; use `--cpu-bind` only after selecting suitable cores for the host computer. Verify device assignment, motion direction, and clear operating space before enabling teleoperation.

## Device checks

**`scan_servos.py`: Scan serial devices.** It probes the selected port at 1 Mbps by default and lists responding device IDs, model numbers, and baud rate. Use it to check the port and device connections. Add `--full` to probe each ID if the default scan misses a device. The tool sends queries only; it does not command homing or movement.

```bash
python tools/scan_servos.py --port /dev/leader_left
python tools/scan_servos.py --port /dev/leader_left --full
```

**`a1z_t_test.py`: Check the A1Z-T device.** It displays joint and trigger positions, temperature, current, voltage, and peak current in real time. Controller button status is also shown by default. Both single-arm and dual-arm checks are supported. On startup, the tool moves the A1Z-T to zero and holds it; press the control button or Enter to release it and start monitoring. Further presses can return it to zero or release it. This tool does not control the A1Z. Clear the A1Z-T operating space before running it.

```bash
python tools/a1z_t_test.py --port /dev/leader_left
python tools/a1z_t_test.py --dual --port /dev/leader_left --port-right /dev/leader_right
```

## License

Original project materials are licensed under the [Galaxea Dynamics A1Z-T LICENSE AGREEMENT](LICENSES.md); see [NOTICE](NOTICE). Bundled components retain their licenses in [a1z_t/licenses](a1z_t/licenses). Keep each adjacent `.pyc.license` notice when redistributing bytecode.
