#!/usr/bin/env python3
"""Provide a localhost-only MAVLink GCS and neutral joystick link for SITL.

This helper deliberately sends no command, mode-change, arm, or disarm
messages.  It exists because PX4's x500 SITL defaults require a live GCS and
joystick input, while the delivery mission correctly refuses to suppress
those safety gates.
"""

import argparse
import signal
import time

from pymavlink import mavutil


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18570)
    parser.add_argument("--rate", type=float, default=10.0)
    return parser.parse_args()


def main():
    args = parse_args()
    if not 1024 <= args.port <= 65535:
        raise SystemExit("REFUSED: port must be within 1024..65535")
    if not 2.0 <= args.rate <= 50.0:
        raise SystemExit("REFUSED: rate must be within 2..50 Hz")

    running = True

    def stop(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    endpoint = f"udpout:127.0.0.1:{args.port}"
    link = mavutil.mavlink_connection(
        endpoint,
        source_system=255,
        source_component=mavutil.mavlink.MAV_COMP_ID_MISSIONPLANNER,
    )
    period = 1.0 / args.rate
    next_send = time.monotonic()
    sequence = 0
    print(
        f"SITL_OPERATOR_LINK_READY endpoint={endpoint} rate_hz={args.rate:.1f} "
        "messages=gcs_heartbeat,neutral_manual_control commands=0",
        flush=True,
    )
    while running:
        link.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0,
            0,
            mavutil.mavlink.MAV_STATE_ACTIVE,
        )
        link.mav.manual_control_send(1, 0, 0, 0, 0, 0)
        sequence += 1
        next_send += period
        delay = next_send - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        else:
            next_send = time.monotonic()

    print(f"SITL_OPERATOR_LINK_STOP messages_each={sequence}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
