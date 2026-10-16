#!/bin/bash
# Copyright (c) 2026 Galaxea Dynamics.
# This file is part of A1Z-T and is licensed under the
# Galaxea Dynamics A1Z-T LICENSE AGREEMENT.
# See LICENSES.md in the project root or https://gitlab.galaxea-ai.com/lemo/a1z-t/-/blob/main/LICENSES.md
# Third-party components retain their respective licenses; see a1z_t/licenses/.
# Modified on 2026-10-16: added license and distribution notices.

# Setup SocketCAN for the two Galaxea Dynamics Isolated USB2CANFD adapters (gs_usb).
# setup_ports.sh assigns can_left/can_right via systemd.link rules.
# Without those rules, warn and fall back to kernel names can0/can1.
#
# Run once after boot (or as a systemd service):
#   bash scripts/setup_can.sh
#
# Legacy single-interface invocation remains supported:
#   bash scripts/setup_can.sh can0

set -e

CAN_NET_CLASS=${CAN_NET_CLASS:-/sys/class/net}
CAN_WAIT_ATTEMPTS=${CAN_WAIT_ATTEMPTS:-100}  # 100 * 0.1 s = 10 s

# Load gs_usb kernel module
sudo modprobe gs_usb

# Bind Galaxea Dynamics Isolated USB2CANFD adapter (VID:PID = a8fa:8598) to gs_usb driver
sudo sh -c 'echo "a8fa 8598" > /sys/bus/usb/drivers/gs_usb/new_id' 2>/dev/null || true

can_interface_exists() {
    [ -e "$CAN_NET_CLASS/$1" ]
}

available_can_interfaces() {
    local path found=0
    for path in "$CAN_NET_CLASS"/can*; do
        [ -e "$path" ] || continue
        printf '%s ' "${path##*/}"
        found=1
    done
    [ "$found" -eq 1 ] || printf '<none>'
}

wait_for_interface() {  # $1 = interface name
    local attempt
    for ((attempt = 0; attempt < CAN_WAIT_ATTEMPTS; attempt++)); do
        can_interface_exists "$1" && return 0
        sleep 0.1
    done
    return 1
}

wait_for_can_count() {  # $1 = expected interface count
    local expected=$1 attempt path count
    for ((attempt = 0; attempt < CAN_WAIT_ATTEMPTS; attempt++)); do
        count=0
        for path in "$CAN_NET_CLASS"/can*; do
            [ -e "$path" ] || continue
            count=$((count + 1))
        done
        [ "$count" -ge "$expected" ] && return 0
        sleep 0.1
    done
    return 1
}

settle_udev() {
    command -v udevadm >/dev/null 2>&1 || return 0
    udevadm settle --timeout=5 || true
}

configure() {  # $1 = interface to configure and bring up
    sudo ip link set "$1" down 2>/dev/null || true
    sudo ip link set "$1" type can bitrate 1000000
    sudo ip link set "$1" txqueuelen 1000
    sudo ip link set "$1" up
}

# Configure only the named interface for legacy invocations.
if [ -n "${1:-}" ]; then
    if ! wait_for_interface "$1"; then
        settle_udev
    fi
    if ! can_interface_exists "$1"; then
        echo "[ERROR] CAN interface $1 was not found after enumeration; available: $(available_can_interfaces)" >&2
        exit 1
    fi
    configure "$1"
    echo "SocketCAN ($1) ready. Verify with: candump $1"
    exit 0
fi

# new_id triggers asynchronous driver probing and systemd.link renaming.
# Wait for both interfaces and udev before deciding which names are present.
echo "[INFO] Waiting for both CAN interfaces and udev naming..."
if ! wait_for_can_count 2; then
    echo "[ERROR] Timed out waiting for two CAN interfaces; available: $(available_can_interfaces)" >&2
    exit 1
fi
settle_udev

LEFT_IF=can_left
RIGHT_IF=can_right
if can_interface_exists can_left && can_interface_exists can_right; then
    :
elif can_interface_exists can0 && can_interface_exists can1 \
        && ! can_interface_exists can_left && ! can_interface_exists can_right; then
    echo "[WARN] can_left/can_right are missing; using can0/can1. Arm assignment depends on kernel enumeration order." >&2
    echo "[WARN] Run bash scripts/setup_ports.sh, then reconnect the adapters or reboot." >&2
    LEFT_IF=can0
    RIGHT_IF=can1
else
    echo "[ERROR] CAN interfaces have incomplete or mixed names: $(available_can_interfaces)" >&2
    echo "[ERROR] Arm assignment cannot be inferred; run bash scripts/setup_ports.sh and reconnect both adapters." >&2
    exit 1
fi

[ -e "$CAN_NET_CLASS/$LEFT_IF" ] || { echo "[ERROR] $LEFT_IF was not found" >&2; exit 1; }
[ -e "$CAN_NET_CLASS/$RIGHT_IF" ] || { echo "[ERROR] $RIGHT_IF was not found" >&2; exit 1; }

configure "$LEFT_IF"
configure "$RIGHT_IF"

echo "SocketCAN ready: $LEFT_IF=left arm $RIGHT_IF=right arm"
echo "Verify with: candump $LEFT_IF / candump $RIGHT_IF"
